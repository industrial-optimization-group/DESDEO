# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
Module description
'''

from abc import ABCMeta


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
    
    def __init__(self, params):
        '''
        Constructor
        '''

    def _objective(self,x):
        '''
        Objective functio to be solved
        '''
        
        objectives,constraints = self.problem.evaluate([x])
        
        objective,new_constraints = self.sclarproblem(objectives)
        
        for ci,const in enumerate(new_constraints):
            constraints[ci].extend(const)
        
        return objective[0],constraints[0]
        
    def minimize(self):
        objective self.problem.evaluate()

class PointSearch(OptimizationMethod):
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
    
    def __init__(self):
        '''
        Constructor
        '''
