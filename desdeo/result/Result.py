# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
"""
from abc import ABCMeta, abstractmethod


class Result(object):
    """
    Abstract base class for result factories to create new results
    """
    __metaclass__ = ABCMeta

    def __init__(self, params):
        """
        Constructor
        """


class Bound(Result):

    def __init__(self, params):
        pass


class Distance(Result):

    def __init__(self, params):
        pass


class IterationPoint(Result):

    def __init__(self, params):
        pass
