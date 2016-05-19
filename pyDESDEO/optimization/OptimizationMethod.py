# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
from boto.gs.cors import METHOD
'''
Module description
'''

from abc import ABCMeta
from scipy.optimize import differential_evolution, minimize
import numpy as np
class OptimizationMethod(object):
    '''
    Brief Description


    Attributes
    ----------
    attr : type
        Description

    Methods
    -------
    method(c='rgb')
        Brief description, methods only for larger classes
    '''
    __metaclass__ = ABCMeta

    def __init__(self):
        '''
        Constructor
        '''

    def search(self, problem):
        '''
        Brief Description


        Attributes
        ----------
        attr : type
            Descrption
        '''


class OptimalSearch(OptimizationMethod):
    '''
    Brief Description


    Attributes
    ----------
    attr : type
        Descrption

    Methods
    -------
    method(c='rgb')
        Brief description, methods only for larger classes
    '''

    def __init__(self, params):
        '''
        Constructor
        '''

class SciPy(OptimalSearch):
    '''
    '''

    def __init__(self, optimization_problem):
        '''
        Constructor
        '''
        self.optimization_problem = optimization_problem

    def _objective(self, x):
        '''
        Objective functio to be solved
        '''

        self.last_objective, self.last_const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        return self.last_objective
        # objective, new_constraints = self.scalarproblem(objectives)

        # for ci, const in enumerate(new_constraints):
        #    constraints[ci].extend(const)

        # return objective[0], constraints[0]
    def _const(self, x, *ncon):
        # self.last_objective, self.last_const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        self.last_objective, self.last_const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        return self.last_const[ncon[0]]

    def search(self, **params):
        nconst = self.optimization_problem.nconst
        constraints = []
        for const in range(nconst):
            constraints.append({"type":"ineq", "fun":self._const, "args":[const]})

        for xi, box in enumerate(self.optimization_problem.problem.bounds()):
            constraints.append({"type":"ineq", "fun":lambda x: box[0] - x[xi], })
            constraints.append({"type":"ineq", "fun":lambda x: x[xi] - box[1], })
            # constraints.append({"type":"ineq", "fun":self.upper, "args":[xi]})
        return minimize(fun=self._objective,
                        x0=self.optimization_problem.problem.starting_point(),
                        method="COBYLA",
                        constraints=constraints,
                         ** params
                        )


class SciPyDE(OptimalSearch):
    '''
    Brief Description


    Attributes
    ----------
    attr : type
        Descrption

    Methods
    -------
    method(c='rgb')
        Brief description, methods only for larger classes
    '''

    def __init__(self, optimization_problem):
        '''
        Constructor
        '''
        self.optimization_problem = optimization_problem
        self.penalty=0.0
    def _objective(self, x):
        '''
        Objective functio to be solved
        '''
        self.penalty = 0.0
        obj, const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        for c in const:
            if c > 0:
                # Lets use Death penalty
                self.penalty = 1000000
        return obj + self.penalty

    def search(self, **params):
        bounds = np.array(self.optimization_problem.problem.bounds())
        np.rot90(bounds)
        res = differential_evolution(func=self._objective, bounds=list(bounds), **params)
        #print "Tot penalty ",self.penalty
        return res

class PointSearch(OptimizationMethod):
    '''
    '''

    def __init__(self):
        '''
        Constructor
        '''
