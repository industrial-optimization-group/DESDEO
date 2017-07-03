# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Copyright (c) 2016  Vesa Ojalehto 

from abc import ABCMeta
import numpy as np

class PreferenceInformation(object):
    __metaclass__ = ABCMeta


    def weights(self):
        ''' Return weight vector corresponding to the given preference information
        '''

class Direction(PreferenceInformation):

    def default_input(self,problem):
        return [0.0]*len(problem.nadir)

    def check_input(self,input,problem):
        return ""


class DirectSpecification(Direction):

    def __init__(self, direction):
        self.pref_input = direction

    def weights(self):
        return np.array(self.pref_input)
    

class PercentageSpecifictation(Direction):

    def __init__(self, percentages):
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


    def __init__(self, ranking):
        self.pref_input = ranking

    def weights(self):
        return 1. / np.array(self.pref_input)


class PairwiseRanking(Direction):

    def __init__(self, selected_obj,other_ranking):
        self.pref_input = (selected_obj,other_ranking)

    def weights(self):
        ranks=self.pref_input[1]
        fi = self.pref_input[0]
        ranks[:fi]+[1.0]+ranks[fi:]
        return ranks



class PreferredPoint(object):
        __metaclass__ = ABCMeta


