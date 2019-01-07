"""
Defines an equilibrium propagation network model
"""
import torch

from typing import List

class EquilibriumNet:
    """
    A fully connected equilibrium propagation network
    """

    # The shape of the equilibrium propagation network as a fully connected
    # network
    shape : List[int]

    @staticmethod
    def get_default_device():
        """
        Get the default device for the equilibrium network's components
        """
        return None

    def __init__(self,
        input_size : int, layer_sizes : List[int], output_size : int, **kwargs):
        """
        Initialize an equilibrium propagation network with given input size,
        output size and fully connected layer sizes on a given device

        >>> new_net = EquilibriumNet(28*28, [500, 500], 10)
        >>> new_net.shape
        [784, 500, 500, 10]
        >>> len(new_net.state_particles), len(new_net.weights), len(new_net.biases)
        (3, 3, 3)
        """
        self.device = kwargs.get("device")
        if self.device is None:
            self.device = self.get_default_device()

        # Get the shape array
        self.shape = [input_size]
        self.shape.extend(layer_sizes)
        self.shape.append(output_size)

        # Initialize the state particles for equilibrium propagation
        self.state_particles = [
            torch.zeros(D) for D in self.shape[1:]
        ]

        # Initialize the weights
        self.weights = [
            torch.randn(D_in, D_out, device=self.device) for (D_in, D_out) in
                zip(self.shape[:-1], self.shape[1:])
        ]

        # Initialize the bias
        self.biases = [
            torch.randn(D, device=self.device) for D in self.shape[:-1]
        ]

    @staticmethod
    def rho(v):
        """
        The activation function to be used, here a hard sigmoid
        >>> EquilibriumNet.rho(torch.tensor([1, 2, -1, -2, 0.5, -0.5]))
        tensor([1.0000, 1.0000, 0.0000, 0.0000, 0.5000, 0.0000])
        """
        return torch.clamp(v, 0, 1)

    @staticmethod
    def rhoprime(v):
        """
        The gradient of the activation function to be used (a hard sigmoid),
        here just a Boolean function denoting whether the value is in the
        clamp range
        >>> EquilibriumNet.rhoprime(torch.tensor([0.9, 2, -1, -2, 0.5, -0.5]))
        tensor([1., 0., 0., 0., 1., 0.])
        """
        return (torch.gt(v, 0) & torch.lt(v, 1)).type(torch.Tensor)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
    print("Doctests complete")
