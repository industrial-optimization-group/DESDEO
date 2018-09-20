# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Copyright (c) 2016  Vesa Ojalehto

from abc import ABCMeta
from typing import Dict, Tuple

import numpy as np

from desdeo.method.base import InteractiveMethod


class PreferenceInformation(object):
    __metaclass__ = ABCMeta

    def __init__(self, method: InteractiveMethod) -> None:
        self._method = method

    def _weights(self) -> np.ndarray:
        return np.array([1.] * self._method.problem.nof_objectives())

    def weights(self):
        """ Return weight vector corresponding to the given preference information
        """
        return self._weights()


class Direction(PreferenceInformation):
    __metaclass__ = ABCMeta

    def default_input(self) -> np.ndarray:
        return np.array([0.0] * len(self._method.problem.nadir))

    def check_input(self, data) -> str:
        return ""


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


class ReferencePoint(PreferenceInformation):

    def __init__(self, method: InteractiveMethod, reference_point=None) -> None:
        super().__init__(method)
        self._reference_point = reference_point

    def reference_point(self):
        """ Return reference point corresponding to the given preference information
        """
        return self._reference_point


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


class NIMBUSClassification(ReferencePoint):
    """
    Preferences by NIMBUS classification

    Attributes
    ----------
    _classification: Dict (objn_n, (class,value))
        NIMBUSClassification information pairing  objective n to  a classification
        with value if needed

    _maxmap: NIMBUSClassification (default:None)
        Minimization - maximiation mapping of classification symbols

    """
    _maxmap = {">": "<", ">=": "<=", "<": ">", "<=": ">=", "=": "="}

    def __init__(self, method: InteractiveMethod, functions, **kwargs) -> None:
        """ Initialize the classification information

        Parameters
        ----------
        functions: list ((class,value)
            Function classification information
        """
        super().__init__(method, **kwargs)
        self._classification: Dict[int, Tuple[str, float]] = {}
        for f_id, v in enumerate(functions):
            # This is classification
            try:
                iter(v)
                self._classification[f_id] = v
            # This is reference point
            except TypeError:
                if np.isclose(v, self._method.problem.ideal[f_id]):
                    self._classification[f_id] = (
                        "<", self._method.problem.selected[f_id]
                    )
                elif np.isclose(v, self._method.problem.nadir[f_id]):
                    self._classification[f_id] = (
                        "<>", self._method.problem.selected[f_id]
                    )
                elif np.isclose(v, self._method.problem.selected[f_id]):
                    self._classification[f_id] = (
                        "=", self._method.problem.selected[f_id]
                    )
                elif (
                    v
                    < self._method.problem.as_minimized(self._method.problem.selected)[
                        f_id
                    ]
                ):
                    self._classification[f_id] = ("<=", v)
                else:
                    self._classification[f_id] = (">=", v)
            else:
                self._classification[f_id] = v

        self._reference_point = self._as_reference_point()
        self._prefrence = self._classification

    def __getitem__(self, key):
        """Shortcut to query a classification."""
        return self._classification[key]

    def __setitem__(self, key, value):
        """Shortcut to manipulate a single classification."""
        self._classification[key] = value

    def with_class(self, cls):
        """ Return functions with the class
        """
        rcls = []
        for key, value in self._classification.items():
            if value[0] == cls:
                rcls.append(key)
        return rcls

    def _as_reference_point(self) -> np.ndarray:
        """ Return classification information as reference point
        """
        ref_val = []
        for fn, f in self._classification.items():
            if f[0] == "<":
                ref_val.append(self._method.problem.ideal[fn])
            elif f[0] == "<>":
                ref_val.append(self._method.problem.nadir[fn])
            else:
                ref_val.append(f[1])

        return np.array(ref_val)


class PreferredPoint(object):
    __metaclass__ = ABCMeta
