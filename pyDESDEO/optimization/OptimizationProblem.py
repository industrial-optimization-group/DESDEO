# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
from _pyio import __metaclass__
'''
Module description
'''

from abc import ABCMeta, abstractmethod
import numpy as np


class OptimizationProblem(object):
    '''
    Brief Description


    Attributes
    ----------
    method : OptimizationMethod instance
        Method used for solving the problem

    '''
    __metaclass__ = ABCMeta

    def __init__(self, method):
        '''
        Constructor
        '''
        self.method=method
    
    @abstractmethod
    def evaluate(self,objectives):
        '''
        evaluate value of the objective function and possible additional constraints
    
    
        Attributes
        ----------
        
        objectives : list of objective values
            Descrption
            
            
        Returns
        -------
        objective : list of floats
            Objective function values corresponding to objectives
        constraint : 2-D matrix of floats
            Constraint function values corresponding to objectives per row. None if no constraints are added
            This must be 2-D matrix for example for NIMBUS scalarizaton        
        '''    
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
    Springer, 1980, pp. 468–486.

    
    '''
    
    def __init__(self, params):
        '''
        Constructor
        '''
        self.reference
        self.weights
        self.rho
        
    
        

    def evaluate(self,objectives):
        
        v_ach=np.vectorize(lambda f,w,r:w*(f-r))
        
        # Calculate achiemvement values
        ach=v_ach(objectives,self.weighs,self.reference)
        
        # Calculate rho_term
        rho_term=np.sum(ach,axis=1)*self.rho
        
        # Calculate maximum of the values for each objective
        max_term = np.max(ach,axis=1)
        
        return max_term+rho_term            
        
        
class EpsilonConstraintProblem(OptimizationProblem):
    '''
    Solves epsilon constraint problem

    math :: \mbox{minimize}     & f_r({\bf{x}}) \\
\mbox{subject to}   &f_j({\bf{x}}) \le z _j, j = 1, \dots, k, j \neq r, \\
                                    & {\bf{x}} \in S, \\

    Attributes
    ----------
    bounds : List of numerical values
        Boundary value for the each of the objectives. The objetive with boundary of None is to be minimized

    
    '''
    
    def __init__(self, obj_bounds=None):
        '''
        Constructor
        '''
        self.obj_bounds=obj_bounds
    
    def evaluate(self,objectives):
        const=[]
        for oi,obj in enumerate(self.obj_bounds):
            if obj is not None:
                const.append(obj)
            else:
                fi = oi
        return np.array(objectives)[:,fi].tolist(), len(objectives)*const
