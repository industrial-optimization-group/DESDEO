# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
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

    def __init__(self, optimization_problem):
        '''
        Constructor
        '''
        self.optimization_problem = optimization_problem

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


class SciPy(OptimalSearch):
    '''
    '''

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
        res = minimize(fun=self._objective,
                        x0=self.optimization_problem.problem.starting_point(),
                        method="COBYLA",
                        constraints=constraints,
                         ** params
                        )
        return self.optimization_problem.problem.evaluate([res.x])[0]


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
        super(SciPyDE, self).__init__(optimization_problem)
        self.penalty=0.0
    def _objective(self, x):
        '''
        Objective functio to be solved
        '''
        self.penalty = 0.0
        obj, const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        if len(const):
            self.v=0.0
            for c in const[0]:
                if c > 0.00001:
                    # Lets use Death penalty
                    self.v+=c
                    self.penalty = 50000000
        return obj[0] + self.penalty

    def search(self, **params):
        bounds = np.array(self.optimization_problem.problem.bounds())
        np.rot90(bounds)
        res = differential_evolution(func=self._objective, bounds=list(bounds), 
                                     popsize=10,
                                     polish=True,
                                     #seed=12432,
                                     maxiter=500000,
                                     tol=0.0000001,
                                     **params)
        if self.penalty and self.v>0.0001:
            print "INFEASIBLE %f"%self.v
        return self.optimization_problem.problem.evaluate([res.x])[0]

class PointSearch(OptimizationMethod):
    '''
    '''
    def search(self, **params):
        obj, const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate())
        a_obj=np.array(obj)

        if const:
            feas = np.all(np.array(const)<0,axis=1)
            if len(feas):
                a_obj[feas==False]=np.inf
            else:
                return None   
        min_i=np.argmin(a_obj)
        return self.optimization_problem.problem.evaluate()[min_i]
