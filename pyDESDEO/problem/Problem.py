# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
Module description
'''

import copy
from abc import abstractmethod, ABCMeta



class Problem(object):
    '''
    Abstract base class for multiobjective problem

    Attributes
    ----------
    attr : type
        Descrption

    Methods
    -------
    method(c='rgb')
        Brief description, methods only for larger classes
    '''
    __metaclass__ = ABCMeta
    
    
    def __init__(self, params):
        '''
        Constructor
        
        '''
        self.variables=[]

    @abstractmethod    
    def evaluate(self, population):
        '''
        Evaluate the objective and constraint functions for population and return tuple (objective,constraint) values 


        Attributes
        ----------
        population : list of variable values
            Descrption
        '''
        pass    

        
    def add_variables(self, variables,index=None):
        '''
        Brief Description
    
    
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
            addvars=copy.deepcopy([variables])
        else:
            addvars=copy.deepcopy(variables)
        
        if index is None:
            self.variables.extend(addvars)
        else:
            self.variables[index:index]=addvars
            


class Variable(object):
    '''
    Brief Description


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
    
    def __init__(self, bounds=None,starting_point=None,name=""):
        '''
        Constructor
        
        
        '''
        self.bounds=bounds
        self.starting_point=starting_point
        self.name=name
        