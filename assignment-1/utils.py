import math
import numpy as np
import random
import torch
import matplotlib.pyplot as plt
import os

class Value : # creating a new "datatype" for ease in understanding
    def __init__(self, data=0, _children=(), _op='', label='') :
        self.data = data
        self.grad = 0 # stores the grad wrt output
        self._backward = lambda: None # stores the backward pass function
        self._prev = set(_children) # stores the children of the variable, to get the DAG
        self._op = _op # stores the operation from which this resulted
        self.label = label
    def __repr__(self) :
        return f'Value(data={self.data}) Label={self.label}' if self.label else f'Value(data={self.data})'
    def __neg__(self) :
        return -1*self
    def __add__(self, other) :
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), '+')
        def _backward() :
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out
    def __radd__(self, other) : # if other+self does not work
        return self + other
    def __sub__(self, other) :
        return self + (-1*other)
    def __rsub__(self, other) :
        return -self + other
    def __mul__(self, other) :
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), '*')
        def _backward() :
            self.grad += out.grad * other.data
            other.grad += out.grad * self.data
        out._backward = _backward
        return out
    def __rmul__(self, other) : # interchanging order of operands if not evaluable
        return self * other
    def __truediv__(self, other) :
        return self * other**-1
    def __rtruediv__(self, other) :
        return other * self**-1
    def __pow__(self, other) :
        assert isinstance(other, (int, float)) 
        val = self.data ** other
        out = Value(val, (self,), f'**{other}')
        def _backward() :
            self.grad += out.grad * other * (self.data ** (other-1)) # does not work if other==0,1
        out._backward = _backward
        return out
    def exp(self) :
        x = self.data
        val = math.exp(x)
        out = Value(val, (self,), 'exp')
        def _backward() :
            self.grad += val * out.grad
        out._backward = _backward
        return out
    def relu(self) :
        x = self.data
        t = x*int(x>0)
        out = Value(t, (self,), 'relu')
        def _backward() :
            self.grad += out.grad * int(t>0)
        out._backward = _backward
        return out
    def sigmoid(self) :
        x = self.data
        t = 1 / (1 + math.exp(-x))
        out = Value(t, (self,), 'sigm')
        def _backward() :
            self.grad = out.grad * t * (1-t)
        out._backward = _backward
        return out
    def tanh(self) :
        x = self.data
        t = math.tanh(x)
        out = Value(t, (self,), 'tanh')
        def _backward() :
            self.grad += out.grad * (1 - t**2)
        out._backward = _backward
        return out
    def backward(self):

        # topological order all of the children in the graph
        topo = []
        visited = set()
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build_topo(child)
                topo.append(v)
        build_topo(self)

        # go one variable at a time and apply the chain rule to get its gradient
        self.grad = 1
        for v in reversed(topo):
            v._backward()


# creating a NN 
class Module :
    def zero_grad(self) :
        for p in self.parameters() :
            p.grad = 0
class Neuron(Module) :
    def __init__(self, ndim) :
        self.w = [Value(random.uniform(-1,1)) for _ in range(ndim)] # array of weights
        self.b = Value(random.uniform(-1,1)) # bias
    def __call__(self, x) :
        # wx + b
        act = sum((wi*xi for wi,xi in zip(self.w, x)), self.b)
        return act.tanh() # only returns tanh activation for now
    def parameters(self) : # giving out list of all params
        return self.w + [self.b] # array of ndim+1 weights
class Layer(Module) :
    def __init__(self, nin, nout) : # nout is the number of neurons in the layer
        self.neurons = [Neuron(nin) for _ in range(nout)]
    def __call__(self,x) :
        return [n(x) for n in self.neurons]
    def parameters(self) :
        # returning each parameter for each neuron
        return [p for neuron in self.neurons for p in neuron.parameters()]
class MLP(Module) :
    def __init__(self, nin, nouts) : # nouts stores the number of neurons in each layer
        sz = [nin] + nouts
        self.layers = [Layer(sz[i], sz[i+1]) for i in range(len(nouts))]
    def __call__(self, x) :
        for layer in self.layers :
            x = layer(x)
        return x
    def parameters(self) :
        return [p for layer in self.layers for p in layer.parameters()]