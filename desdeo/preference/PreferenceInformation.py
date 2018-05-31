# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Copyright (c) 2016  Vesa Ojalehto

from abc import ABCMeta

import numpy as np


class PreferenceInformation(object):
    __metaclass__ = ABCMeta

    def __init__(self, method):
        self._method = method

    def _weights(self):
        return np.array([1.] * self._method.problem.nof_objectives())
        pass

    def weights(self):
        """ Return weight vector corresponding to the given preference information
        """
        return self._weights()


class Direction(PreferenceInformation):
    __metaclass__ = ABCMeta

    def default_input(self):
        return [0.0] * len(self._method.problem.nadir)

    def check_input(self, data):
        return ""


class PercentageSpecifictation(Direction):

    def __init__(self, problem, percentages):
        super().__init__(problem)
        self.pref_input = percentages

    def _weights(self):
        return np.array(self.pref_input) / 100.

    def default_input(self):
        return [0] * len(self._method.problem.nadir)

    def check_input(self, input):
        inp = np.array(input).astype(float)
        if np.sum(inp) != 100:
            return "Total sum of preferences should be 100"
        return ""


class RelativeRanking(Direction):

    def __init__(self, problem, ranking):
        super().__init__(problem)
        self.pref_input = ranking

    def _weights(self):
        return 1. / np.array(self.pref_input)


class PairwiseRanking(Direction):

    def __init__(self, problem, selected_obj, other_ranking):
        super().__init__(problem)
        self.pref_input = (selected_obj, other_ranking)

    def _weights(self):
        ranks = self.pref_input[1]
        fi = self.pref_input[0]
        ranks[:fi] + [1.0] + ranks[fi:]
        return ranks


class ReferencePoint(PreferenceInformation):

    def __init__(self, method, reference_point=None):
        super().__init__(method)
        self._reference_point = reference_point

    def reference_point(self):
        """ Return reference point corresponding to the given preference information
        """
        return self._reference_point


class DirectSpecification(Direction, ReferencePoint):

    def __init__(self, method, direction, reference_point=None):
        super().__init__(method, **{"reference_point": reference_point})
        self.pref_input = direction

    def _weights(self):
        return np.array(self.pref_input)

    def reference_point(self):
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

    def __init__(self, method, functions, **kwargs):
        """ Initialize the classification information

        Parameters
        ----------
        functions: list ((class,value)
            Function classification information
        """
        super().__init__(method, **kwargs)
        self.__classification = {}
        for f_id, v in enumerate(functions):
            # This is classification
            try:
                iter(v)
                self.__classification[f_id] = v
            # This is reference point
            except TypeError:
                if np.isclose(v, self._method.problem.ideal[f_id]):
                    self.__classification[f_id] = (
                        "<", self._method.problem.selected[f_id]
                    )
                elif np.isclose(v, self._method.problem.nadir[f_id]):
                    self.__classification[f_id] = (
                        "<>", self._method.problem.selected[f_id]
                    )
                elif np.isclose(v, self._method.problem.selected[f_id]):
                    self.__classification[f_id] = (
                        "=", self._method.problem.selected[f_id]
                    )
                elif (
                    v
                    < self._method.problem.as_minimized(self._method.problem.selected)[
                        f_id
                    ]
                ):
                    self.__classification[f_id] = ("<=", v)
                else:
                    self.__classification[f_id] = (">=", v)
            else:
                self.__classification[f_id] = v

        self._reference_point = self.__as_reference_point()
        self._prefrence = self.__classification

    def __getitem__(self, key):
        """Shortcut to query a classification."""
        return self.__classification[key]

    def __setitem__(self, key, value):
        """Shortcut to manipulate a single classification."""
        self.__classification[key] = value

    def with_class(self, cls):
        """ Return functions with the class
        """
        rcls = []
        for key, value in self.__classification.items():
            if value[0] == cls:
                rcls.append(key)
        return rcls

    def __as_reference_point(self):
        """ Return classification information as reference point
        """
        ref_val = []
        for fn, f in self.__classification.items():
            if f[0] == "<":
                ref_val.append(self._method.problem.ideal[fn])
            elif f[0] == "<>":
                ref_val.append(self._method.problem.nadir[fn])
            else:
                ref_val.append(f[1])

        return ref_val


class PreferredPoint(object):
    __metaclass__ = ABCMeta
