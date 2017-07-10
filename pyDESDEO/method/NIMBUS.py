# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2017  Vesa Ojalehto

'''
Synchronous NIMBUS method

Miettinen, K. & Mäkelä, M. M.
Synchronous approach in interactive multiobjective optimization
European Journal of Operational Research, 2006, 170, 909-922
'''
import logging


from Method import Method
from optimization.OptimizationProblem import AchievementProblem, NIMBUSProblem
from core.ResultFactory import IterationPointFactory

class NIMBUS(Method):
    ''''
    Abstract class for optimization methods


    Attributes
    ----------
    _preference : Classification (default:None)
        Preference, i.e., classification information  information for current iteration

    '''
    __SCALARS = ["NIM","ACH"]
    def __init__(self, problem, method_class):
        super(NIMBUS, self).__init__(problem, method_class)
        self._factories = []
        self._factories.append(IterationPointFactory(self.method_class(NIMBUSProblem(self.problem))))
        self._factories.append(IterationPointFactory(self.method_class(AchievementProblem(self.problem))))
        self._classification = None
        self._problem = problem

    def _nextIteration(self, *args, **kwargs):
        try:
            self._classification = kwargs["preference"]
        except KeyError:
            logging.error("Failed to obtain preferences for NIMBUS method")
        try:
            self._scalars = kwargs["scalars"]
        except KeyError:
            self._scalars = self.__SCALARS
        po = []
        for scalar in self._scalars:
            po.append(list(self._factories[self.__SCALARS.index(scalar)].result(self._classification)))
        return po

