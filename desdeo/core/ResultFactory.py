# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto

from abc import ABC
from typing import List, Tuple

import numpy as np


class ResultFactory(ABC):
    """
    Abstract base class for result factories
    """


class BoundsFactory(ResultFactory):
    """Specifies an object that can generate bounds for an EpsilonConstraintProblem.

    Attributes
    ----------
    optimization_method : OptimizationMethod
        The optimization method which contains the EpsilonConstraintProblem problem
        the bounds should be generated for.
    """
    def __init__(self, optimization_method):
        """Initializer

        Variables
        ---------
        optimization_method : OptimizationMethod
            See BoundsFactory's attributes.
        """
        self.optimization_method = optimization_method

    def result(self, prev_point, upper=False):
        """Generates the bounds for the optimization problem contained in
        optimization_method.

        Variables
        ---------
        prev_point : List[float]
            Specifies the previous point, according to which, the bounds for the next
            point should be generated.
        upper : bool, optional
            By default, result returns the lower bounds. If True, returns the upper bounds.

        Returns
        -------
        List[float] : The lower bounds of the optimization problem contained in
            optimization_method. If upper is True, then this function returns the
            upper bounds instead.
        """
        Phr = []
        for fi, fr in enumerate(prev_point):
            # fi == index, fr == value of element at index
            # optimization_problem must be an EpsilonConstraintProblem! (Only implementation with
            # an obj_bounds attribute.)
            self.optimization_method.optimization_problem.obj_bounds = list(prev_point)
            self.optimization_method.optimization_problem.obj_bounds[fi] = None
            _, bound = self.optimization_method.search(upper)
            if bound is None:
                # No new solution found, using the previous value
                Phr.append(prev_point[fi])
            else:
                # New best solution found, use that
                Phr.append(bound[fi])

        return Phr


class IterationPointFactory(ResultFactory):
    """Specifies an object that can generate iteration points for iterative optimization
    methods according to some preference.

    Attributes
    ----------
    optimization_method : OptimizationMethod
        The optimization method which contains the optimiation problem
        the iteration point should be generated for.
    last_solution : Tuple[np.ndarray, List[float]]
        A tuple containing the decision and objective objective vectors respectively.

    Returns
    -------
    Tuple[np.ndarray, List[float]] : last_solution, see above.
    """
    def __init__(self, optimization_method):
        """Initializer.

        Variables
        ---------
        optimization_method : OptimizationMethod
            See IterationPointFactory's attributes.
        """
        self.optimization_method = optimization_method

    def result(self, preferences, prev_point) -> Tuple[np.ndarray, List[float]]:
        """Generates the iteration point according from a preference and previous point.

        Variables
        ---------
        preferences : ReferencePoint
            A preference point specified by a decision makes.
        """
        self.optimization_method.optimization_problem.set_preferences(
            preferences, prev_point
        )
        #        self.optimization_method.optimization_problem.weights = preferences.weights()
        #        self.optimization_method.optimization_problem.reference = preferences.reference_point()
        self.last_solution = self.optimization_method.search()
        return self.last_solution
