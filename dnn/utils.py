from __future__ import annotations

import functools
from typing import Generator

import numpy as np

from dnn.loss import Loss


def loss_factory(loss: str) -> Loss:
    registry = Loss.get_loss_classes()
    cls = registry.get(loss)
    if cls is None:
        raise ValueError("Loss with this name does not exist")
    return cls()


def generate_batches(
    X: np.ndarray, Y: np.ndarray, batch_size: int, shuffle: bool = True
) -> Generator[tuple[np.ndarray, np.ndarray, int], None, None]:
    num_samples = X.shape[-1]

    if batch_size > num_samples:
        raise ValueError(
            "The batch size is greater than the number of samples in the dataset"
        )

    num_full_batches = int(np.floor(num_samples / batch_size))

    if shuffle is True:
        perm = np.random.permutation(num_samples)
        X, Y = X[..., perm], Y[..., perm]

    if num_full_batches == 1:
        yield X, Y, num_samples
        return

    for idx in range(num_full_batches):
        start = idx * batch_size
        end = (idx + 1) * batch_size
        yield X[..., start:end], Y[..., start:end], batch_size

    if num_samples % batch_size != 0:
        start = batch_size * num_full_batches
        yield X[..., start:], Y[..., start:], num_samples - start


def backprop(
    model: "Model",
    loss: Loss,
    labels: np.ndarray,
    preds: np.ndarray,
    reg_param: float = 0.0,
) -> None:
    dA = loss.compute_derivatives(labels, preds)

    for layer in reversed(model.layers):
        dA = layer.backprop_step(dA, reg_param=reg_param)


def compute_l2_cost(model: "Model", reg_param: float, cost: float) -> float:
    norm = np.add.reduce([np.linalg.norm(layer.weights) ** 2 for layer in model.layers])

    m = model.ip_layer.ip.shape[-1]

    return cost + (reg_param * norm) / (2 * m)


def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))


def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition(".")
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)
