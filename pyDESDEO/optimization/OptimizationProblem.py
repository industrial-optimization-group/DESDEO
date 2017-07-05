# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
from _pyio import __metaclass__
'''
Module description
'''

import abc
import numpy as np


class OptimizationProblem(object):
    '''
    Single objective optimization problem


    Attributes
    ----------
    problem : OptimizationMethod instance
        Method used for solving the problem

    '''
    __metaclass__ = abc.ABCMeta

    def __init__(self, problem):
        '''
        Constructor
        '''
        self.nconst = 0
        self.problem = problem
        

    def evaluate(self, objectives):
        '''
        Evaluate value of the objective function and possible additional constraints


        Attributes
        ----------

        objectives : list of objective values

        Returns
        -------
        objective : list of floats
            Objective function values corresponding to objectives
        constraint : 2-D matrix of floats
            Constraint function values corresponding to objectives per row. None if no constraints are added
        '''
        return self._evaluate(objectives)
    
    @abc.abstractmethod
    def _evaluate(self,objectives):
        pass

class AchievementProblem(OptimizationProblem):
    '''
    Finds new solution by solving achievement scalarizing function[1]_

    math :: \mbox{minimize}     & \displaystyle{\max_{i=1, \dots , k}\left\{\, \mu_i(f_i(\mathbf x) - q_i)\ \right\}} + \rho \sum_{i=1}^k \mu_i (f_i(\mathbf x)- q_i) \\
\mbox{subject to}   & {\bf{x}} \in S, \\


    References
    ----------

    [1] A. P. Wierzbicki, The use of reference objectives in multiobjective optimization, in: G. Fandel, T. Gal (Eds.),
    Multiple Criteria Decision Making, Theory and Applications, Vol. 177 of Lecture Notes in Economics and Mathematical Systems,
    Springer, 1980, pp. 468-486.
    '''

    def __init__(self, problem, eps=0.00001, rho=0.01):
        super(AchievementProblem, self).__init__(problem)
        self.reference = []
        self.eps = eps
        self.scaling_weights = list(1.0 / (np.array(self.problem.nadir) - (np.array(self.problem.ideal) - self.eps)))
        self.weights = [1.0] * len(self.problem.nadir)
        self.rho = rho


    def _evaluate(self, objectives):
        v_ach = np.vectorize(lambda f, w, r:w * (f - r))

        # Calculate achievement values
        ach_rho = v_ach(objectives, np.array(self.scaling_weights), self.reference)

        # Calculate rho_term
        rho_term = np.sum(ach_rho, axis=1) * self.rho

        # Calculate maximum of the values for each objective
        ach = v_ach(objectives, np.array(self.scaling_weights) * np.array(self.weights), self.reference)
        max_term = np.max(ach, axis=1)
        return max_term + rho_term, []


class EpsilonConstraintProblem(OptimizationProblem):
    '''
    Solves epsilon constraint problem

    math :: \mbox{minimize}     & f_r({\bf{x}}) \\
\mbox{subject to}   &f_j({\bf{x}}) \le z _j, j = 1, \dots, k, j \neq r, \\
                                    & {\bf{x}} \in S, \\

    Attributes
    ----------
    bounds : List of numerical values
        Boundary value for the each of the objectives. The objective with boundary of None is to be minimized


    '''

    def __init__(self, problem, obj_bounds=None):
        super(EpsilonConstraintProblem,self).__init__(problem)
        self.obj_bounds = obj_bounds
        self.objective = 100000
 

    def _evaluate(self, objectives):
        objs=[]
        consts=[]
        for ind in objectives:
            const = []
            for oi, obj in enumerate(self.obj_bounds):
                if obj:
                    const.append(ind[oi] - obj)
                else:
                    fi = oi
            objs.append(ind[fi])
            consts.append(const)
        
        return objs,consts
    
