# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto

from abc import ABCMeta
from typing import List, Tuple

import numpy as np


class ResultFactory(object):
    """
    Abstract base class for result factories

    """
    __metaclass__ = ABCMeta


class BoundsFactory(ResultFactory):

    def __init__(self, optimization_method):
        self.optimization_method = optimization_method

    def result(self, prev_point, upper=False):
        Phr = []
        for fi, fr in enumerate(prev_point):
            self.optimization_method.optimization_problem.obj_bounds = list(prev_point)
            self.optimization_method.optimization_problem.obj_bounds[fi] = None
            _, bound = self.optimization_method.search(upper)
            if bound is None:
                Phr.append(prev_point[fi])
            else:
                Phr.append(bound[fi])

        return Phr


class IterationPointFactory(ResultFactory):

    def __init__(self, optimization_method):
        self.optimization_method = optimization_method

    def result(self, preferences, prev_point) -> Tuple[np.ndarray, List[float]]:
        self.optimization_method.optimization_problem.set_preferences(
            preferences, prev_point
        )
        #        self.optimization_method.optimization_problem.weights = preferences.weights()
        #        self.optimization_method.optimization_problem.reference = preferences.reference_point()
        self.last_solution = self.optimization_method.search()
        return self.last_solution
