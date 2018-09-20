# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
This module contains the abstract base class for all interactive methods.
"""
from abc import ABC, abstractmethod


class InteractiveMethod(ABC):
    """
    Abstract base class for interactive multiobjective methods.
    """

    def __init__(self, problem, method_class):
        self.problem = problem
        self.method_class = method_class

    @abstractmethod
    def _next_iteration(self, *args, **kwargs):
        pass

    def next_iteration(self, *args, **kwargs):
        """
        Return solution(s) for the next iteration
        """
        return self._next_iteration(*args, **kwargs)

    @abstractmethod
    def _init_iteration(self, *args, **kwargs):
        pass

    def init_iteration(self, *args, **kwargs):
        """
        Return the initial solution(s)
        """
        return self._init_iteration(*args, **kwargs)
