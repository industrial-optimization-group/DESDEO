# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
Module description
'''
from abc import abstractmethod, ABCMeta
from scipy.optimize import differential_evolution, minimize
import numpy as np

class OptimizationMethod(object):
    '''
    Brief Description


    Attributes
    ----------
    _max : bool (default:False)
        True if the objective function is to be maximized

    _ceoff : float
        Coefficient for the objective function
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

    def search(self, max=False, **params):
        '''
        Search for the optimal solution

        This sets up the search for the optimization and calls the _search method
        
        Attributes
        ----------
        max : boold (default False)
            If true find mximum of the objective function instead of minimum
        
        **params : dict [optional]
            Parameters for single objective optimization method
        '''

        self._max=max
        if max:
            self._coeff=-1.0
        else:
            self._coeff=1.0
        
        return self._search(**params)

    @abstractmethod
    def _search(self, **params):
        '''
        The actual search for the optimal solution   

        This is an abstract class that must be implemented by the subclasses

         Attributes
        ----------
        **params : dict [optional]
            Parameters for single objective optimization method
        '''

        pass

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
        return self._coeff*self.last_objective
        # objective, new_constraints = self.scalarproblem(objectives)

        # for ci, const in enumerate(new_constraints):
        #    constraints[ci].extend(const)

        # return objective[0], constraints[0]
    def _const(self, x, *ncon):
        # self.last_objective, self.last_const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        self.last_objective, self.last_const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate([x]))
        return self.last_const[ncon[0]]

    def _search(self, max=False, **params):
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
        return self._coeff*obj[0] + self.penalty

    def _search(self,**params):
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
    def _search(self, **params):
        obj, const = self.optimization_problem.evaluate(self.optimization_problem.problem.evaluate())
        a_obj=np.array(obj)

        if const:
            feas = np.all(np.array(const)<0,axis=1)
            if len(feas):
                a_obj[feas==False]=self._coeff*np.inf
            else:
                return None   
        if self._max:
            optarg=np.argmax
        else:
            optarg=np.argmin
        opt_i=optarg(a_obj)
        return self.optimization_problem.problem.evaluate()[opt_i]
