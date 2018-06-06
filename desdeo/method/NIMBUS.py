# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2017  Vesa Ojalehto

"""
Synchronous NIMBUS method

Miettinen, K. & Mäkelä, M. M.
Synchronous approach in interactive multiobjective optimization
European Journal of Operational Research, 2006, 170, 909-922
"""
import logging
from typing import List, Tuple

import numpy as np

from desdeo.core.ResultFactory import IterationPointFactory
from desdeo.optimization.OptimizationProblem import (
    NIMBUSAchievementProblem,
    NIMBUSGuessProblem,
    NIMBUSProblem,
    NIMBUSStomProblem,
)
from desdeo.preference import NIMBUSClassification

from .base import InteractiveMethod


class NIMBUS(InteractiveMethod):
    """'
    Abstract class for optimization methods


    Attributes
    ----------
    _preference : ClNIMBUSClassificationdefault:None)
        Preference, i.e., classification information  information for current iteration

    """
    __SCALARS = ["NIM", "ACH", "GUESS", "STOM"]

    def __init__(self, problem, method_class):
        super().__init__(problem, method_class)
        self._factories = [
            IterationPointFactory(self.method_class(prob_cls(self.problem)))
            for prob_cls in [
                NIMBUSProblem,
                NIMBUSAchievementProblem,
                NIMBUSGuessProblem,
                NIMBUSStomProblem,
            ]
        ]
        self._classification = None
        self._problem = problem
        self.selected_solution = None

    def _next_iteration(self, *args, **kwargs) -> List[Tuple[np.ndarray, List[float]]]:
        try:
            self._classification = kwargs["preference"]
        except KeyError:
            logging.error("Failed to obtain preferences for NIMBUS method")
        if "scalars" in kwargs:
            self._scalars = kwargs["scalars"]
        elif "num_scalars" in kwargs:
            num_scalars = int(kwargs["num_scalars"])
            self._scalars = self.__SCALARS[:num_scalars]
        else:
            self._scalars = self.__SCALARS
        po = []
        for scalar in self._scalars:
            po.append(
                self._factories[self.__SCALARS.index(scalar)].result(
                    self._classification, self.selected_solution
                )
            )
        return po

    def _init_iteration(self, *args, **kwargs) -> List[Tuple[np.ndarray, List[float]]]:
        ref = (np.array(self.problem.nadir) - np.array(self.problem.ideal)) / 2
        cls = []
        # Todo calculate ideal and nadir values
        for v in ref:
            cls.append(("<=", v))
        self.selected_solution = self._factories[self.__SCALARS.index("ACH")].result(
            NIMBUSClassification(self, cls), self.selected_solution
        )
        return [self.selected_solution]
