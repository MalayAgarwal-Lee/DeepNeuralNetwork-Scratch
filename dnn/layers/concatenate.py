from typing import List, Optional, Tuple

from collections import Iterator

import numpy as np

from .base_layer import LayerInput, MultiInputBaseLayer


class Concatenate(MultiInputBaseLayer):
    """Concatenates two or more inputs along a particular axis.

    Inherits from
    ---------
    MultiInputBaseLayer

    Attributes
    ---------
    axis: int
        Axis along which the inputs should be concatenated.

    concatenated: np.ndarray
        Output of the layer after concatenation.

    Input shape
    ----------
    (..., batch_size), where ... represents any number of dimensions.

    Output shape
    ----------
    (..., x, ..., batch_size), where x is the sum of the dimension
    along the concatenation axis of each input
    and ... represents any number of dimensions.

    Example
    ----------
    >>> import numpy as np
    >>> from dnn import Input
    >>> from dnn.layers import Concatenate

    >>> ip1 = Input(shape=(3, None)) # Create first input
    >>> ip1.ip = np.array([[1, 2], [3, 4], [5, 6]])

    >>> ip2 = Input(shape=(3, None)) # Create second input
    >>> ip2.ip = np.array([[7, 8], [9, 10], [11, 12]])

    >>> layer = Concatenate(ip=[ip1, ip2])
    >>> layer.forward_step() # Forward step
    array([[ 1,  2],
           [ 3,  4],
           [ 5,  6],
           [ 7,  8],
           [ 9, 10],
           [11, 12]])
    >>> layer.output_shape() # 6 = 3 + 3
    (6, 2)
    """

    def __init__(self, ip: List[LayerInput], axis: int = 0, name: str = None) -> None:
        """
        Arguments
        ---------
        ip: Inputs to the layer.

        axis: Axis along which the inputs should be concatenated. Defaults to 0.

        name: Name of the layer. Should be unique in a model.
        When None, a name is automatically generated.

        Raises
        ----------
        ValueError: When all inputs do not have the same shape
        except along the concatenation axis.
        """
        super().__init__(ip, trainable=False, name=name)

        self._validate_same_shape(axis)

        self.axis = axis
        self.concatenated = None

    def _get_axis_excluded_shapes(self, axis: int) -> Iterator[Tuple]:
        """Method to get the shape of the inputs without the dimension along axis.

        Arguments
        ---------
        axis: Axis which should be excluded from each shape.
        """
        return (
            tuple(dim for i, dim in enumerate(shape) if i != axis)
            for shape in self.input_shape()
        )

    def _validate_same_shape(self, axis: int) -> None:
        """Method to validate that all inputs have the same shape except along axis.

        Arguments
        ----------
        axis: Axis which should be excluded during validation.

        Raises
        ----------
        ValueError: When all inputs do not have the same shape.
        """
        shapes = self._get_axis_excluded_shapes(axis)

        first_shape = next(shapes)

        if any(shape != first_shape for shape in shapes):
            msg = (
                "All inputs must have the same shape, except along the concatenation axis. "
                f"Expected shape (excluding the concatenation axis): {first_shape}."
            )
            raise ValueError(msg)

    def output(self) -> Optional[np.ndarray]:
        return self.concatenated

    def output_shape(self) -> Tuple:
        axis = self.axis

        shapes = self.input_shape()

        first_shape = shapes[0]

        in_axis_dim = first_shape[axis]

        # The concatenation axis refers to batch_size and the
        # Complete shape of the inputs is not known to the layer
        if in_axis_dim is None:
            return first_shape

        # Since all other dimensions except the concatenation axis
        # remain unchanged, a list is created to copy over the dimensions and
        # the concatenation axis is modified
        shape = list(first_shape)
        shape[axis] = sum((shape[axis] for shape in shapes[1:]), in_axis_dim)

        return tuple(shape)

    def forward_step(self, *args, **kwargs) -> np.ndarray:
        """Method to carry out one step of forward propagation.

        Raises
        ---------
        ValueError: When all inputs do not have the same shape
        excluding the concatenation axis.
        """
        # Need to recheck since the batch_size, which may have been None
        # During __init__() is also available now.
        self._validate_same_shape(self.axis)

        self.concatenated = np.concatenate(self.input(), axis=self.axis)

        return self.concatenated

    def _split_indices(self) -> List[int]:
        """Method to obtain the indices where the gradient should be split."""
        shapes = self.input_shape()

        axis = self.axis

        running_sum = shapes[0][axis]

        indices = [running_sum]

        for shape in shapes[1:-1]:
            dim = shape[axis]
            running_sum += dim
            indices.append(running_sum)

        return indices

    def backprop_inputs(self, grad: np.ndarray, *args, **kwargs) -> Tuple[np.ndarray]:
        indices = self._split_indices()

        # Split the gradient along the concatenation axis
        return tuple(np.split(grad, indices_or_sections=indices, axis=self.axis))
