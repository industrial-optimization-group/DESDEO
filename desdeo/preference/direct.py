import numpy as np

from desdeo.method.base import InteractiveMethod

from .base import Direction, ReferencePoint


class PercentageSpecifictation(Direction):

    def __init__(self, method: InteractiveMethod, percentages: np.ndarray) -> None:
        super().__init__(method)
        self.pref_input = percentages

    def _weights(self) -> np.ndarray:
        return np.array(self.pref_input) / 100.

    def default_input(self) -> np.ndarray:
        return np.array([0] * len(self._method.problem.nadir))

    def check_input(self, input) -> str:
        inp = np.array(input).astype(float)
        if np.sum(inp) != 100:
            return "Total sum of preferences should be 100"
        return ""


class RelativeRanking(Direction):

    def __init__(self, method: InteractiveMethod, ranking) -> None:
        super().__init__(method)
        self.pref_input = ranking

    def _weights(self) -> np.ndarray:
        return 1. / np.array(self.pref_input)


class PairwiseRanking(Direction):

    def __init__(self, method: InteractiveMethod, selected_obj, other_ranking) -> None:
        super().__init__(method)
        self.pref_input = (selected_obj, other_ranking)

    def _weights(self) -> np.ndarray:
        ranks = self.pref_input[1]
        fi = self.pref_input[0]
        ranks[:fi] + [1.0] + ranks[fi:]
        return np.array(ranks)


class DirectSpecification(Direction, ReferencePoint):

    def __init__(
        self, method: InteractiveMethod, direction: np.ndarray, reference_point=None
    ) -> None:
        super().__init__(method, **{"reference_point": reference_point})
        self.pref_input = direction

    def _weights(self) -> np.ndarray:
        return self.pref_input

    def reference_point(self) -> np.ndarray:
        return self.weights()
