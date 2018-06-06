# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""Miscellaneous utilities
"""

import datetime
import sys
from typing import List, Tuple

import numpy as np
from sklearn.cluster.k_means_ import KMeans
from sklearn.metrics.pairwise import pairwise_distances_argmin_min

from desdeo.core.ResultFactory import IterationPointFactory
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


def _centroids(n_clusters: int, points: List[List[float]]) -> List[List[float]]:
    """ Return n_clusters centroids of points
    """

    k_means = KMeans(n_clusters=n_clusters)
    k_means.fit(points)

    closest, _ = pairwise_distances_argmin_min(k_means.cluster_centers_, points)

    return list(map(list, np.array(points)[closest.tolist()]))


def random_weights(nobj: int, nweight: int) -> List[List[float]]:
    """ Generatate nw random weight vectors for nof objectives as per Tchebycheff method [SteCho83]_

    .. [SteCho83] Steuer, R. E. & Choo, E.-U. An interactive weighted Tchebycheff procedure for multiple objective programming, Mathematical programming, Springer, 1983, 26, 326-344

    Parameters
    ----------
    nobj:
        Number of objective functions

    nweight:
        Number of weights vectors to be generated

    Returns
    -------
    List[List[float]
        nobj x nweight matrix of weight vectors


    """

    # Initial wector space as per
    # Miettinen, K. Nonlinear Multiobjective Optimization
    # Kluwer Academic Publishers, 1999
    wspace = 50 * nobj
    while wspace < nweight:
        wspace *= 2

    weights = np.random.rand(wspace, nobj)
    return _centroids(nobj, weights)


def new_points(
    factory: IterationPointFactory, solution, weights: List[List[float]] = None
) -> List[Tuple[np.ndarray, List[float]]]:
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
        Direction of the projection, if not given generate with
        :func:random_weights

    """
    points = []
    nof = factory.optimization_method.optimization_problem.problem.nof_objectives()
    if not weights:
        weights = random_weights(nof, 50 * nof)
    for pref in map(
        lambda w: DirectSpecification(factory.optimization_method, w), weights
    ):
        points.append(factory.result(pref, solution))
    return points


def as_minimized(values: List[float], maximized: List[bool]) -> List[float]:
    """ Return vector values as minimized
    """
    return [v * -1. if m else v for v, m in zip(values, maximized)]
