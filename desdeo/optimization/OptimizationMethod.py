# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
This module contains methods for solving single-objective optimization problems.
"""
from abc import ABCMeta, abstractmethod
from typing import List, Tuple

import numpy as np
from scipy.optimize import differential_evolution, minimize


class OptimizationMethod(object, metaclass=ABCMeta):
    """
    Abstract class for optimization methods

    Attributes
    ----------
    _max : bool (default:False)
        True if the objective function is to be maximized

    _ceoff : float
        Coefficient for the objective function
    """

    def __init__(self, optimization_problem):
        self.optimization_problem = optimization_problem

    def search(self, max=False, **params) -> Tuple[np.ndarray, List[float]]:
        """
        Search for the optimal solution

        This sets up the search for the optimization and calls the _search method

        Parameters
        ----------
        max : bool (default False)
            If true find mximum of the objective function instead of minimum

        **params : dict [optional]
            Parameters for single objective optimization method
        """

        self._max = max
        if max:
            self._coeff = -1.0
        else:
            self._coeff = 1.0

        return self._search(**params)

    @abstractmethod
    def _search(self, **params) -> Tuple[np.ndarray, List[float]]:
        """
        The actual search for the optimal solution

        This is an abstract class that must be implemented by the subclasses

        Parameters
        ----------
        **params : dict [optional]
            Parameters for single objective optimization method
        """

        pass


class OptimalSearch(OptimizationMethod, metaclass=ABCMeta):
    """
    Abstract class for optimal search
    """

    @abstractmethod
    def _objective(self, x):
        """
        Return objective function value

        Parameters
        ----------
        x : list of values
            Decision variable vector to be calclated
        """


class SciPy(OptimalSearch):
    """
    """

    def _objective(self, x):
        self.last_objective, self.last_const = self.optimization_problem.evaluate(
            self.optimization_problem.problem.evaluate([x])
        )
        return self._coeff * self.last_objective
        # objective, new_constraints = self.scalarproblem(objectives)

        # for ci, const in enumerate(new_constraints):
        #    constraints[ci].extend(const)

        # return objective[0], constraints[0]

    def _const(self, x, *ncon):
        # self.last_objective, self.last_const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        self.last_objective, self.last_const = self.optimization_problem.evaluate(
            self.optimization_problem.problem.evaluate([x])
        )
        return self.last_const[ncon[0]]

    def _search(self, max=False, **params) -> Tuple[np.ndarray, List[float]]:
        nconst = self.optimization_problem.nconst
        constraints = []
        for const in range(nconst):
            constraints.append({"type": "ineq", "fun": self._const, "args": [const]})

        for xi, box in enumerate(self.optimization_problem.problem.bounds()):
            constraints.append({"type": "ineq", "fun": lambda x: box[0] - x[xi]})
            constraints.append({"type": "ineq", "fun": lambda x: x[xi] - box[1]})
            # constraints.append({"type":"ineq", "fun":self.upper, "args":[xi]})
        res = minimize(
            fun=self._objective,
            x0=self.optimization_problem.problem.starting_point(),
            method="COBYLA",
            constraints=constraints,
            **params
        )
        return self.optimization_problem.problem.evaluate([res.x])[0]


class SciPyDE(OptimalSearch):

    def __init__(self, optimization_problem):
        super().__init__(optimization_problem)
        self.penalty = 0.0

    def _objective(self, x):
        self.penalty = 0.0
        obj, const = self.optimization_problem.evaluate(
            self.optimization_problem.problem.evaluate([x])
        )
        if const is not None and len(const):
            self.v = 0.0
            for c in const[0]:
                if c > 0.00001:
                    # Lets use Death penalty
                    self.v += c
                    self.penalty = 50000000
        return self._coeff * obj[0] + self.penalty

    def _search(self, **params) -> Tuple[np.ndarray, List[float]]:
        bounds = np.array(self.optimization_problem.problem.bounds())
        np.rot90(bounds)
        res = differential_evolution(
            func=self._objective,
            bounds=list(bounds),
            popsize=10,
            polish=True,
            # seed=12432,
            maxiter=500000,
            tol=0.0000001,
            **params
        )
        if self.penalty and self.v > 0.0001:
            print("INFEASIBLE %f" % self.v)
        return res.x, self.optimization_problem.problem.evaluate([res.x])[0]


class PointSearch(OptimizationMethod):

    def _search(self, **params) -> Tuple[np.ndarray, List[float]]:
        evl = self.optimization_problem.problem.evaluate()
        obj, const = self.optimization_problem.evaluate(evl)
        a_obj = self._coeff * np.array(obj)

        if const is not None and len(const):
            # Using penalty for handling constraint violations
            viol = np.sum(np.array(const).clip(0, None), axis=1)
            a_obj += viol

        opt_i = np.argmin(a_obj)
        return opt_i, self.optimization_problem.problem.evaluate()[opt_i]
