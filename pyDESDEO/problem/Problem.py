# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto

import copy
from abc import abstractmethod, ABCMeta
import numpy as np

from pyDESDEO.utils.misc import as_minimized

class Problem(object):
    '''
    Abstract base class for multiobjective problem

    Attributes
    ----------
    variables : list of Variables
        Problem decision variable information

    ideal
        Ideal, i.e, the worst values of objective functions

    nadir
        Nadir, i.e, the best values of objective functions

    maximized
        Indicates maximized objectives
    '''
    __metaclass__ = ABCMeta


    def __init__(self, ideal = None, nadir = None, maximized = None, objectives = None, name = None):
        self.variables = []
        self.ideal = ideal
        self.nadir = nadir
        if maximized is not None:
            self.maximized = maximized
        elif self.ideal is not None:
            self.maximized = [False] * len(self.ideal)
        else:
            self.maximzed = None

        self.objectives = objectives
        self.name = name

        if self.ideal and self.nadir:
            self.maximum = self.as_minimized([i if m else n for i, n, m in zip(ideal, nadir, self.maximized)])
            self.minimum = self.as_minimized([n if m else i for i, n, m in zip(ideal, nadir, self.maximized)])


    @abstractmethod
    def evaluate(self, population):
        '''
        Evaluate the objective and constraint functions for population and return tuple (objective,constraint) values


        Attributes
        ----------
        population : list of variable values
            Description
        '''
        pass

    def objective_bounds(self):
        '''
        Return objective bounds


        Returns
        -------
        lower : list of floats
            Lower boundaries for the objectives

        Upper : list of floats
            Upper boundaries for the objectives

        '''
        if self.ideal and self.nadir:
            return self.ideal, self.nadir
        raise NotImplementedError("Ideal and nadir value calculation is not yet implemented")

    def nof_objectives(self):
        assert len(self.ideal) == len(self.nadir)
        return len(self.ideal)

    def nof_variables(self):
        return len(self.variables)

    def add_variables(self, variables, index = None):
        '''
        Attributes
        ----------
        variable : list of variables or single variable
            Add variables as problem variables

        index : int
            Location to add variables, if None add to the end

        '''
        try:
            variables[0]
        except TypeError:
            addvars = copy.deepcopy([variables])
        else:
            addvars = copy.deepcopy(variables)

        if index is None:
            self.variables.extend(addvars)
        else:
            self.variables[index:index] = addvars

    def as_minimized(self, v):
            return as_minimized(v, self.maximized)

class Variable(object):
    '''
    Attributes
    ----------
    bounds : list of numeric values
        lower and upper boundaries of the variable

    name : string
        Name of the variable

    starting_point : numeric value
        Starting point for the variable

    Methods
    -------
    method(c='rgb')
        Brief description, methods only for larger classes
    '''

    def __init__(self, bounds = None, starting_point = None, name = ""):
        '''
        Constructor


        '''
        self.bounds = bounds
        self.starting_point = starting_point
        self.name = name


class PreGeneratedProblem(Problem):
    ''' A problem where the objective function values have beeen pregenerated
    '''
    def __init__(self, filename = None, points = None, delim = ","):
        super(PreGeneratedProblem, self).__init__()

        self.points = []
        if points is not None:
            self.points = list(points)
        elif filename is not None:
            with open(filename) as fd:
                for r in fd:
                    self.points.append(map(float, map(str.strip, r.split(delim))))
        else:
            assert len(self.points)
        if not self.ideal:
            self.ideal = list(np.min(self.points, axis = 0))
        if not self.nadir:
            self.nadir = list(np.max(self.points, axis = 0))


    def evaluate(self, population = None):
        return self.points


