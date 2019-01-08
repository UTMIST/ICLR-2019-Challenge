"""
Defines an equilibrium propagation network model
"""
import torch
import itertools
import operator

from typing import List

def rho(v):
    """
    The activation function to be used, here a hard sigmoid
    >>> rho(torch.tensor([1, 2, -1, -2, 0.5, -0.5]))
    tensor([1.0000, 1.0000, 0.0000, 0.0000, 0.5000, 0.0000])
    """
    return torch.clamp(v, 0, 1)

def rhoprime(v):
    """
    The gradient of the activation function to be used (a hard sigmoid),
    here just a Boolean function denoting whether the value is in the
    clamp range
    >>> rhoprime(torch.tensor([0.9, 2, -1, -2, 0.5, -0.5]))
    tensor([1., 0., 0., 0., 1., 0.])
    """
    return (torch.gt(v, 0) & torch.lt(v, 1)).type(torch.Tensor)

class EquilibriumNet:
    """
    A fully connected feed-forward equilibrium propagation network
    """

    # The shape of the equilibrium propagation network as a fully connected
    # network
    # shape: List[int]
    # partial_sums: List[int]

    # The size of minibatches to be fed into the equilibrium propagation network
    # minibatch_size : int

    @staticmethod
    def get_default_device():
        """
        Get the default device for the equilibrium network's components
        """
        return "cpu"

    def set_batch_size(self, minibatch_size : int, **kwargs):
        """
        Reinitialize the state with the given minibatch size
        """
        self.minibatch_size = minibatch_size

        self.minibatch_size = minibatch_size

        # Initialize the state particles for equilibrium propagation
        self.state_particles = kwargs.get("initial_state")
        if self.state_particles is None:
            self.state_particles =\
                torch.zeros(self.partial_sums[-1], minibatch_size)
        elif len(self.state_particles.shape) == 1:
            self.state_particles = torch.t(
                self.state_particles.repeat(minibatch_size, 1))
            assert self.state_particles.shape[0] == self.partial_sums[-1],\
                "Got shape {}, expected length {}".format(
                    self.state_particles.shape, self.partial_sums[-1]
                )
        else:
            assert tuple(self.state_particles.shape) == (
                self.partial_sums[-1], minibatch_size
            ), "Bad shape: {}".format(tuple(self.state_particles.shape))

        # State particles for the neurons in each individual layer,
        # implemented as views of the memory in state_particles
        self.layer_state_particles = [
            self.state_particles[b:e] for (b, e) in
                zip(self.partial_sums[:-1], self.partial_sums[1:])
        ]

    def __init__(self,
        input_size : int, layer_sizes : List[int], output_size : int,
        minibatch_size : int, **kwargs):
        """
        Initialize an equilibrium propagation network with given input size,
        output size and fully connected layer sizes on a given device

        >>> new_net = EquilibriumNet(28*28, [500, 500], 10, 32)
        >>> new_net.shape
        [784, 500, 500, 10]
        >>> len(new_net.state_particles), len(new_net.biases)
        (1010, 1010)
        >>> len(new_net.weights), len(new_net.layer_biases)
        (3, 3)
        >>> len(new_net.input_weights)
        1784
        """
        self.device = kwargs.get("device")
        if self.device is None:
            self.device = self.get_default_device()

        # Get the shape array
        self.shape = [input_size]
        self.shape.extend(layer_sizes)
        self.shape.append(output_size)

        # Get the number of particles and bias parameters before each layer, and
        # one past-the-end
        self.partial_sums = [0]
        self.partial_sums.extend(
            itertools.accumulate(self.shape[1:], operator.add))

        self.set_batch_size(minibatch_size,
            initial_state = kwargs.get("initial_state"))

        # Initialize the weights
        self.weights = kwargs.get("weights")
        if self.weights is None:
            self.weights = [
                torch.randn(D_out, D_in, device=self.device) for (D_in, D_out) in
                    zip(self.shape[:-1], self.shape[1:])
            ]
        else:
            assert len(self.weights) == len(self.shape) - 1
            for weights, D_in, D_out in\
                zip(self.weights, self.shape[:-1], self.shape[1:]):
                assert weights.shape == (D_out, D_in),\
                    "Got weight shape {}, expected {}".format(
                        weights.shape, (D_out, D_in))

        # Get a vector of input neurons weights for each state neuron
        self.input_weights = list(
            itertools.chain.from_iterable(
                [[w[p] for p in range(len(w))] for w in self.weights]
            )
        )

        # Initialize the bias
        self.biases = kwargs.get("biases")
        if self.biases is None:
            self.biases = torch.randn(self.partial_sums[-1])
        else:
            assert len(self.biases) == self.partial_sums[-1]

        # Bias for the neurons in each individual layer, implemented as views of
        # the memory in biases
        self.layer_biases = [
            self.biases[b:e] for (b, e) in
                zip(self.partial_sums[:-1], self.partial_sums[1:])
        ]

    def energy(self, x):
        """
        The "potential energy" of the equilibrium propagation network for in its
        current state for each input in x, where x is a tensor of shape
        (minibatch_size, input_size)
        """
        # 2nd argument was self.input_size. -Matt
        assert x.shape == (self.minibatch_size, self.shape[0])

        # Squared norm of the state
        # LaTeX: \frac{1}{2}\sum_{i \in \mathcal{S}}s_i^2
        squared_norm = torch.sum(self.state_particles ** 2, dim=0) / 2


        # Product of bias and state activation
        # LaTeX: \sum_{i \in \mathcal{S}}b_i\rho(s_i)
        bias_sum = torch.matmul(self.biases, rho(self.state_particles))

        # Tensor product of weight matrix, activation of non-state neurons j and
        # activation of non-state neurons i connected to j
        #
        # Due to the structure of our network (feed-forward), neurons in layers
        # after the first, potentially including the output (last) layer, are
        # connected to state neurons in the previous layer, giving the form of
        # our calculation


        # Matrix product of the weight matrix for a layer and the activation of
        # neurons in that layer.
        next_weights = [
            torch.mm(torch.t(W), rho(s_out)) for W, s_out in
                zip(self.weights[1:], self.layer_state_particles[1:])
        ]

        # Dot product of said matrix products and the activations of the vectors
        # connected to j, summed over all layers
        tensor_product = sum(
            [torch.matmul(torch.t(pr), rho(s_in)).diag() for pr, s_in in
                zip(next_weights, self.layer_state_particles[:-1])]
        )

        # Tensor product of weight matrix, activation of non-state neurons j and
        # activation of input neurons i connected to j for each input value in x
        #
        # Due to the structure of our network, only neurons in the layer after
        # the first are connected to the input neurons, and hence we need only
        # consider these
        input_sums = -torch.mm(
            x, torch.mm(torch.t(self.weights[0]), rho(self.layer_state_particles[0]))
        ).diag()

        # Now, we compute the energy for each element of x
        return input_sums + squared_norm - bias_sum - tensor_product

    def energy_grad_state(self, x):
        """
        Gradient of energy with respect to each component of the current state
        for each component of the minibatch x
        """
        assert x.shape == (self.minibatch_size, self.shape[0])

        # Get the derivative of the activation for the state for each batch
        dact = rhoprime(self.state_particles)


        print("weight: {}".format([w.shape for w in self.weights]))
        print("layer: {}".format([l.shape for l in self.layer_state_particles]))

        res = [torch.matmul(weights, layer) for weights, layer in
            zip(self.weights[1:], self.layer_state_particles[:-1])]

        print("res: {}".format([r.shape for r in res]))

        res = torch.cat(res)
        input_product = torch.nn.functional.pad(
                torch.matmul(self.weights[0], torch.t(x)),
                (0, self.partial_sums[-1] - self.shape[0])
            )

        print("res: {}, input: {}".format(res.shape, input_product.shape))

    def energy_grad_weight(self, state, x):
        """
        Gradient of energy with respect to the weights
        """
        assert state.shape == self.state_particles.shape

        activated_state = rho(state)

        bias_grad = torch.mean(activated_state, dim=1)

        # TODO: this code is copied from constructor

        layer_states = [torch.t(x)]
        layer_states += [
            activated_state[b:e] for (b, e) in
            zip(self.partial_sums[:-1], self.partial_sums[1:])
        ]

        weight_grad = [
            torch.mm(next_activated_state, torch.t(prev_activated_state)) / self.minibatch_size
            for (prev_activated_state, next_activated_state) in
            zip(layer_states[:-1], layer_states[1:])
        ]

        return weight_grad, bias_grad


if __name__ == "__main__":
    import doctest
    doctest.testmod()
    print("Doctests complete")
