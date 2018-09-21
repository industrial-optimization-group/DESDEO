from abc import ABC

import numpy as np

from desdeo.method.base import InteractiveMethod


class PreferenceInformation(ABC):

    def __init__(self, method: InteractiveMethod) -> None:
        self._method = method

    def _weights(self) -> np.ndarray:
        return np.array([1.] * self._method.problem.nof_objectives())

    def weights(self):
        """ Return weight vector corresponding to the given preference information
        """
        return self._weights()


class Direction(PreferenceInformation):

    def default_input(self) -> np.ndarray:
        return np.array([0.0] * len(self._method.problem.nadir))

    def check_input(self, data) -> str:
        return ""


class ReferencePoint(PreferenceInformation):

    def __init__(self, method: InteractiveMethod, reference_point=None) -> None:
        super().__init__(method)
        self._reference_point = reference_point

    def reference_point(self):
        """ Return reference point corresponding to the given preference information
        """
        return self._reference_point
