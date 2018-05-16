# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
"""

import datetime
import logging
import sys
from typing import List

from desdeo.preference.PreferenceInformation import DirectSpecification


class Tee(object):
    """ Duplicate stdout to a logfile. Duplicates functionality of a tee command

    Note that Tee instance will replace stdout until it has been deleted.
    """

    def __init__(self, logfile, date_format="%Y-%m-%d %H:%M"):
        self.terminal = sys.stdout
        sys.stdout = self
        self.date_format = date_format
        format = logging.Formatter(
            "%(asctime)-12s %(levelname)-6s %(message)s", "%Y-%m-%d %H:%M:%S")

        flog = logging.FileHandler(logfile)
        flog.setFormatter(format)
        self.log = open(logfile, "a")

    def write(self, message):

        self.terminal.write(message)
        if len(message.strip()):
            self.log.write(f"{datetime.datetime.now():%Y-%m-%d %H-%m:%S} {message}")
        else:
            self.log.write(f"{message}")

    def __del__(self):
        sys.stdout = self.terminal
        self.file.close()

    def flush(self):
        self.log.flush()


def new_points(factory, solution, weights):
    points = []
    for pref in map(lambda w: DirectSpecification(factory.problem, w), weights):
        points.append(factory.result(pref, solution))
    return points


def as_minimized(values: List[float], maximized: List[bool]) -> List[float]:
    """ Return vector values as minimized
    """
    return [v * -1. if m else v for v, m in zip(values, maximized)]
