# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto

import copy
from abc import ABCMeta, abstractmethod
from typing import List, Optional, Union

import numpy as np

from desdeo.utils.misc import as_minimized


class MOProblem(object):
    """
    Abstract base class for multiobjective problem

    Attributes
    ----------
    variables : list of Variables
        MOProblem decision variable information

    ideal
        Ideal, i.e, the worst values of objective functions

    nadir
        Nadir, i.e, the best values of objective functions

    maximized
        Indicates maximized objectives
    """
    __metaclass__ = ABCMeta

    def __init__(
        self,
        nobj: int,
        nconst: int = 0,
        ideal: Optional[List[float]] = None,
        nadir: Optional[List[float]] = None,
        maximized: Optional[List[bool]] = None,
        objectives: Optional[List[str]] = None,
        name: str = None,
        points: Optional[List[float]] = None,
    ) -> None:
        self.nobj = nobj
        self.nconst = nconst
        self.variables = []  # type: List[Variable]
        self.ideal = ideal
        self.nadir = nadir
        self.points = points
        if maximized is not None:
            self.maximized = maximized  # type: Optional[List[bool]]
        elif self.ideal is not None:
            self.maximized = [False] * len(self.ideal)
        else:
            self.maximized = None

        if objectives is None:
            self.objectives = ["f%i" % (i + 1) for i in range(self.nobj)]
        else:
            self.objectives = objectives
        self.name = name

        if self.ideal and self.nadir and self.maximized:
            self.maximum = self.as_minimized(
                [
                    i if m else n
                    for i, n, m in zip(self.ideal, self.nadir, self.maximized)
                ]
            )
            self.minimum = self.as_minimized(
                [
                    n if m else i
                    for i, n, m in zip(self.ideal, self.nadir, self.maximized)
                ]
            )

    @abstractmethod
    def evaluate(self, population):
        """
        Evaluate the objective and constraint functions for population and return tuple (objective,constraint) values


        Parameters
        ----------
        population : list of variable values
            Description
        """

    def objective_bounds(self):
        """
        Return objective bounds


        Returns
        -------
        lower : list of floats
            Lower boundaries for the objectives

        Upper : list of floats
            Upper boundaries for the objectives

        """
        if self.ideal and self.nadir:
            return self.ideal, self.nadir
        raise NotImplementedError(
            "Ideal and nadir value calculation is not yet implemented"
        )

    def nof_objectives(self) -> Optional[int]:
        if self.ideal and self.nadir:
            assert len(self.ideal) == len(self.nadir)
            return len(self.ideal)
        else:
            return None

    def nof_variables(self) -> int:
        return len(self.variables)

    def add_variables(
        self, variables: Union[List["Variable"], "Variable"], index: int = None
    ) -> None:
        """
        Parameters
        ----------
        variable : list of variables or single variable
            Add variables as problem variables

        index : int
            Location to add variables, if None add to the end

        """
        if isinstance(variables, Variable):
            addvars = copy.deepcopy([variables])
        else:
            addvars = copy.deepcopy(variables)

        if index is None:
            self.variables.extend(addvars)
        else:
            self.variables[index:index] = addvars

    def as_minimized(self, v):
        return as_minimized(v, self.maximized)

    def bounds(self):

        return [v.bounds for v in self.variables]


class PythonProblem(MOProblem):
    pass


class Variable(object):
    """
    Attributes
    ----------
    bounds : list of numeric values
        lower and upper boundaries of the variable

    name : string
        Name of the variable

    starting_point : numeric value
        Starting point for the variable
    """

    def __init__(self, bounds=None, starting_point=None, name=""):
        """
        Constructor


        """
        self.bounds = bounds
        self.starting_point = starting_point
        self.name = name


class PreGeneratedProblem(MOProblem):
    """ A problem where the objective function values have beeen pregenerated
    """

    def __init__(self, filename=None, points=None, delim=",", **kwargs):
        self.points = []
        self.original_points = []
        if points:
            self.original_points = list(points)
            self.points = list(points)
        elif filename:
            with open(filename) as fd:
                for r in fd:
                    self.points.append(list(map(float, map(str.strip, r.split(delim)))))
            self.original_points = list(self.points)

        super().__init__(nobj=len(self.points[0]), points=self.points, **kwargs)

        if not self.ideal:
            self.ideal = list(np.min(self.points, axis=0))
        if not self.nadir:
            self.nadir = list(np.max(self.points, axis=0))

    def evaluate(self, population=None):
        return self.points
