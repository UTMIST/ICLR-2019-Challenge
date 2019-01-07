"""
Tests for EquilibriumNet.
"""

from equilibrium import EquilibriumNet, rho
import torch


def test_energy():
    x = torch.tensor([[1, 2, 3], [4, 5, 6]])
    w1 = torch.tensor([[3, 9, 5], [1, 2, 7], [3, 3, 2]])
    w2 = torch.tensor([[3, 8, 8], [9, 5, 1]])
    w3 = torch.tensor([[9, 2], [2, 0]])
    b = torch.tensor([1, 2, 3, 4, 5, 6, 7, 8])  # for x, l2, l3

    l2 = torch.tensor([9, 4, 6])
    l3 = torch.tensor([5, 3])
    l4 = torch.tensor([4, 5])

    squared_norm = (torch.sum(l2) ** 2 +
                    torch.sum(l3) ** 2 + torch.sum(l4) ** 2) / 2

    first = torch.cat((l2, l3), 0)
    second = torch.cat((first, l4), 0)
    bias_sum = torch.sum(b * rho(second))

    prod1 = torch.dot(torch.mv(w2.T, l3), l2)
    prod2 = torch.dot(torch.mv(w3.T, l4), l3)
    tensor_product = sum(prod1, prod2)

    input_sums = -torch.mv(x, torch.mv(w1.T, l2))  # Apply rho to l2?

    energy = input_sums.add(squared_norm - bias_sum - tensor_product)

    assert True  # compare with class


def test_energy_grad_state():
    """
    Check energy_grad_state is correct using finite differences.
    """
    x = torch.tensor([[1, 2, 3], [4, 5, 6]])
    w1 = torch.tensor([[3, 9, 5], [1, 2, 7], [3, 3, 2]])
    w2 = torch.tensor([[3, 8, 8], [9, 5, 1]])
    w3 = torch.tensor([[9, 2], [2, 0]])
    b = torch.tensor([1, 2, 3, 4, 5, 6, 7])  # for l2, l3, l4

    l2 = torch.tensor([9, 4, 6])
    l3 = torch.tensor([5, 3])
    l4 = torch.tensor([4, 5])

    network = EquilibriumNet(28 * 28, [3, 2], 2, 1)
    network.weights = [w1, w2, w3]
    network.biases = b
    network.state_particles = torch.cat([l2, l3, l4])

    # perform gradient checking with finite differences
    dh = 10e-5
    for i in range(3 + 2 + 2):
        # perturb one entry in state
        network.state_particles[i] += dh
        f_plus = network.energy(x)
        network.state_particles[i] -= 2 * dh
        f_minus = network.energy(x)
        network.state_particles[i] += dh

        # grad estimate with finite differences
        grad_check = (f_plus - f_minus) / (2 * dh)

        true_grad = network.energy_grad_state(x)  # TODO: implement

        assert relative_error(grad_check, true_grad) < 10e-6


def relative_error(a, b):
    """
    Compute relative error between a and b.
    """
    return abs(a - b) / (abs(a) + abs(b))
