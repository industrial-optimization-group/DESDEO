# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto <vesa.ojalehto@gmail.com>
from problem.Problem import Problem
from result.Result import IterationPoint
from core.ResultFactory import IterationPointFactory, BoundsFactory
from optimization.OptimizationProblem import AchievementProblem, \
    EpsilonConstraintProblem
'''
NAUTILUS method variants

NAUTILUS    The first NAUTILUS variant by Miettinen, K.; Eskelinen, P.; Ruiz, F. & Luque, M.

TODO
----
Longer description of the method variants and methods
'''
import numpy as np
from Method import Method

def printCurrentIteration(method):
        print "Iteration %s/%s" % (method.user_iters - method.current_iter, method.user_iters)
        print "DISTANCE: ", method.distance()
        print "Lower boundary:", method.fh_lo
        print "Iteration point:", method.zh
        print "=============================="


class NAUTILUS(Method):
    '''
    The first NAUTILUS method variant[1]_

    References
    ----------

    [1] Miettinen, K.; Eskelinen, P.; Ruiz, F. & Luque, M.,
        NAUTILUS method: An interactive technique in multiobjective optimization based on the nadir point,
        European Journal of Operational Research, 2010 , 206 , 426-434.
    '''


    def __init__(self, problem, method_class):
        '''
        Constructor
        '''
        self.problem = problem
        self.method_class = method_class
        self.user_iters = 5
        self.current_iter = self.user_iters
        self.fh_factory = IterationPointFactory(self.method_class(AchievementProblem(self.problem)))
        self.bounds_factory = BoundsFactory(self.method_class(EpsilonConstraintProblem(self.problem)))
        self.preference = None

        self.fh_lo, self.zh = tuple(self.problem.objective_bounds())
        self.fh = self.fh_lo
        self.zh_prev=self.zh

        # self.zh = self.zh_pref = self.fh = self.fh_lo = None

    def __update_fh(self):
        self.fh = list(self.problem.evaluate([self.fh_factory.result(self.preference, self.zh_prev)])[0])
    
    def __update_zh(self):
        self.zh_prev = self.zh
        self.__update_fh()

        self.zh = list((self.current_iter - 1.) / self.current_iter * np.array(self.zh_prev) + (1. / self.current_iter) * np.array(self.fh))

    def nextIteration(self, preference=None):
        '''
        Return next iteration bounds
        '''
        if preference:
            self.preference=preference
        self.__update_fh()
        
        #tmpzh = list(self.zh)
        self.__update_zh()
        #self.zh = list(np.array(self.zh) / 2. + np.array(self.zh_prev) / 2.)
        #self.zh_prev = tmpzh


        self.fh_lo = list(self.bounds_factory.result(self.zh_prev))

        self.current_iter -= 1

        return self.fh_lo, self.zh
