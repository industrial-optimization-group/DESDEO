# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
'''
Module description
'''

from abc import ABCMeta, abstractmethod
import numpy as np

class PreferenceInformation(object):
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
    __metaclass__ = ABCMeta


    def __init__(self, params):
        '''
        Constructor
        '''
    def weights(self):
        ''' Return weight vector corresponding to the given preference information
        '''

class Direction(PreferenceInformation):
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
    def default_input(self,problem):
        return [0.0]*len(problem.nadir)

    def check_input(self,input,problem):
        return ""


class DirectSpecification(Direction):
    '''
     '''

    def __init__(self, direction):
        '''
        Constructor
        '''

        self.pref_input = direction

    def weights(self):
        return np.array(self.pref_input)
    

class PercentageSpecifictation(Direction):
    '''
     '''

    def __init__(self, percentages):
        '''
        Constructor
        '''

        self.pref_input = percentages

    def weights(self):
        return np.array(self.pref_input)/100.

    def default_input(self,problem):
        return [0]*len(problem.nadir)

    def check_input(self,input,problem):
        inp=map(float,input)
        if np.sum(inp)!=100:
            return "Total of the preferences should be 100"
        return ""



class RelativeRanking(Direction):
    '''
     '''

    def __init__(self, ranking):
        '''
        Constructor
        '''

        self.pref_input = ranking

    def weights(self):
        return 1. / np.array(self.pref_input)


class PairwiseRanking(Direction):
    '''
     '''

    def __init__(self, selected_obj,other_ranking):
        '''
        Constructor
        '''

        self.pref_input = (selected_obj,other_ranking)

    def weights(self):
        ranks=self.pref_input[1]
        fi = self.pref_input[0]
        ranks[:fi]+[1.0]+ranks[fi:]
        return ranks



class PreferredPoint(object):
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
