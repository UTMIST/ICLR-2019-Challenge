"""
For training the model
"""
import time

import numpy as np

from data import load_data
from equilibrium import Equilibrium

SEED = 0


def train(hyperparams: dict):
    """
    Train the model with <hyperparams>.
    """

    train, val, test = load_data(0.8)  # TODO: train/val split ratio?

    model = Equilibrium(hyperparams["alpha"])

    # get number of examples
    train_size = train[0].shape[1]
    for epoch in range(hyperparams["epochs"]):
        time0 = time.time()
        # shuffle train set
        shuffled_indices = [i for i in range(train_size)]
        np.random.shuffle(shuffled_indices)

        for minibatch in range(int(np.ceil(train_size/hyperparams["minibatch"]))):
            # if minibatch % 100 == 0:
            #     print(epoch, minibatch)
            x_sample = train[0][:, shuffled_indices[minibatch * hyperparams["minibatch"]:
                                                    (minibatch + 1) * hyperparams["minibatch"]]]
            y_sample = train[1][:, shuffled_indices[minibatch * hyperparams["minibatch"]:
                                                    (minibatch + 1) * hyperparams["minibatch"]]]
            beta = (2 * np.random.randint(0, 2) - 1) * hyperparams["beta"]  # random sign
            s_neg = model.negative_phase(x_sample, hyperparams["t-"], hyperparams["epsilon"])
            s_pos = model.positive_phase(x_sample, y_sample, hyperparams["t+"], hyperparams["epsilon"], beta)

            model.update_weights(beta, hyperparams["etas"], s_pos, s_neg, x_sample)

        print(time.time() - time0)


if __name__ == "__main__":
    hyperparams = {
        "epsilon": 0.5,             # step size
        "beta": 0.5,                # clamping factor
        "etas": [0.1, 0.05],        # learning rate
        "t+": 4,                    # # of pos phase steps
        "t-": 20,                   # # of neg phase steps
        "alpha": (784, 500, 10),    # architecture, specified as sizes of hidden layers
        "minibatch": 20,
        "epochs": 25
    }
    train(hyperparams)
