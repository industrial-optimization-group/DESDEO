# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""Miscellaneous utilities
"""

import datetime
import sys
from typing import List

from desdeo.preference.PreferenceInformation import DirectSpecification


class Tee(object):
    """ Appends  stdout to a logfile.

    Note that a Tee instance will replace stdout until it has been deleted.
    """

    def __init__(self, logfile, date_format="%Y-%m-%d %H:%M"):
        self.terminal = sys.stdout
        sys.stdout = self
        self.date_format = date_format
        self.log = open(logfile, "a")
        self.__buffer = ""

    def write(self, message):

        self.terminal.write(message)
        self.__buffer += message
        if "\n" in self.__buffer:
            self.log.write(
                f"{datetime.datetime.now():{self.date_format}} {self.__buffer}"
            )
            self.__buffer = ""

    def __del__(self):
        sys.stdout = self.terminal
        self.log.close()

    def flush(self):
        self.log.flush()


def new_points(factory, solution, weights):
    """Generate approximate set of points

    Generate set of Pareto optimal solutions projecting from the Pareto optimal solution
    using weights to determine the direction.


    Parameters
    ----------

    factory:
        IterationPointFactory with suitable optimization problem

    solution:
        Current solution from which new solutions are projected

    weights:
        Direction of the projection
    """
    points = []
    for pref in map(
        lambda w: DirectSpecification(factory.optimization_method, w), weights
    ):
        points.append(factory.result(pref, solution))
    return points


def as_minimized(values: List[float], maximized: List[bool]) -> List[float]:
    """ Return vector values as minimized
    """
    return [v * -1. if m else v for v, m in zip(values, maximized)]
