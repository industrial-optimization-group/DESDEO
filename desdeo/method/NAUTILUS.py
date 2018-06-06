# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
NAUTILUS method variants

NAUTILUS    The first NAUTILUS variant introduces in
            Miettinen, K.; Eskelinen, P.; Ruiz, F. & Luque, M.
            NAUTILUS method: An interactive technique in multiobjective
                optimization based on the nadir point
            European Journal of Operational Research, 2010, 206, 426-434

TODO
----
Add all variants
Longer descriptions of the method variants and methods
"""
import logging
from typing import List, Tuple, Type  # noqa - rm when pyflakes understands type hints
from warnings import warn

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin_min

import desdeo.utils as utils
from desdeo.core.ResultFactory import BoundsFactory, IterationPointFactory
from desdeo.optimization.OptimizationMethod import OptimizationMethod
from desdeo.optimization.OptimizationProblem import (
    EpsilonConstraintProblem,
    MaxEpsilonConstraintProblem,
    NautilusAchievementProblem,
)
from desdeo.preference.PreferenceInformation import DirectSpecification
from desdeo.utils import misc, reachable_points
from desdeo.utils.warnings import UnexpectedCondition

from .base import InteractiveMethod


class NAUTILUS(InteractiveMethod):

    def __init__(self, method, method_class: Type[OptimizationMethod]) -> None:
        super().__init__(method, method_class)
        self.user_iters = 5
        self.current_iter = self.user_iters

        self.fh_factory = IterationPointFactory(
            self.method_class(NautilusAchievementProblem(self.problem))
        )
        self.upper_bounds_factory = BoundsFactory(
            self.method_class(MaxEpsilonConstraintProblem(self.problem))
        )
        self.lower_bounds_factory = BoundsFactory(
            self.method_class(EpsilonConstraintProblem(self.problem))
        )

        self.preference = None

        self.fh_lo, self.zh = tuple(self.problem.objective_bounds())
        self.fh = list(self.fh_lo)
        self.zh_prev = list(self.zh)

    def _init_iteration(self, *args, **kwargs):
        pass

    def _next_iteration(self, *args, **kwargs):
        pass

    def _update_fh(self):
        self.fh = list(self.fh_factory.result(self.preference, self.zh_prev)[1])

    def _next_zh(self, term1, term2):
        res = list(
            (self.current_iter - 1)
            * np.array(term1)
            / self.current_iter
            + np.array(term2)
            / self.current_iter
        )
        logging.debug("Update zh")
        logging.debug("First term:  %s", term1)
        logging.debug("Second term: %s", term2)
        for i in range(3):
            logging.debug(
                "%i/%i * %f + %f/%i  =%f",
                (self.current_iter - 1),
                self.current_iter,
                term1[i],
                term2[i],
                self.current_iter,
                res[i],
            )
        return res

    def _update_zh(self, term1, term2):
        self.zh_prev = list(self.zh)

        self.zh = list(self._next_zh(term1, term2))

    def distance(self, where: List[float], target: List[float]):

        a_nadir = np.array(self.problem.nadir)
        a_ideal = np.array(self.problem.ideal)
        w = a_ideal - a_nadir
        u = np.linalg.norm((np.array(where) - a_nadir) / w)
        l = np.linalg.norm((np.array(target) - a_nadir) / w)
        logging.debug("\nNADIR: %s", self.problem.nadir)
        logging.debug("zh: %s", where)
        logging.debug("PO: %s", target)
        if not l:
            logging.debug("Distance: %s", 0.0)
            return 0.0
        logging.debug("Distance: %s", (u / l) * 100)
        return (u / l) * 100


class ENAUTILUS(NAUTILUS):

    def __init__(self, method, method_class: Type[OptimizationMethod]) -> None:
        super().__init__(method, method_class)
        self.Ns = 5
        self.fh_lo_prev = None
        self.fh_lo_prev = None

        self.nsPoint_prev = []  # type: List[float]

        self.zhs = []  # type: List[float]
        self.zh_los = []  # type: List[float]
        self.zh_reach = []  # type: List[int]

        self.NsPoints = []  # type: List[Tuple[np.ndarray, List[float]]]

    def print_current_iteration(self):
        if self.current_iter < 0:
            print("Final iteration point:", self.zh_prev)
        else:
            print(
                "Iteration %s/%s\n"
                % (self.user_iters - self.current_iter, self.user_iters)
            )

            for pi, ns_point in enumerate(self.NsPoints):
                print(
                    "Ns %i (%s)" % (pi + 1, self.zh_reach[pi] if self.zh_reach else "-")
                )
                print("Iteration point:", self.zhs[pi])
                if self.current_iter != 0:
                    print("Lower boundary: ", self.zh_los[pi])
                print("Closeness: ", self.distance(self.zhs[pi], ns_point))

            print("==============================")

    def _update_zh(self, term1, term2):

        return self._next_zh(term1, term2)

    def select_point(self, point):
        pass

    def next_iteration(self, *args, preference=None, **kwargs):
        if preference and preference[0]:
            self.zh_prev = list(preference[0])
        else:
            self.zh_prev = self.problem.nadir[:]
        if preference and preference[1]:
            self.fh_lo = list(preference[1])
        else:
            self.fh_lo = self.problem.ideal[:]

        # TODO Create weights if not given, e.g., using
        # Steuer RE, Choo EU. An interactive weighted Tchebycheff procedure for
        # multiple objective programming.
        # Mathematical programming. 1983; 26(3):326-44.

        points = misc.new_points(self.fh_factory, self.zh)

        # Find centroids
        if len(points) <= self.Ns:
            print(
                (
                    "Only %s points can be reached from selected iteration point"
                    % len(points)
                )
            )
            self.NsPoints = points
        else:
            # k-mean cluster Ns solutions
            k_means = KMeans(n_clusters=self.Ns)
            solution_points = [points[1] for point in points]
            k_means.fit(solution_points)

            closest = set(
                pairwise_distances_argmin_min(
                    k_means.cluster_centers_, solution_points
                )[
                    0
                ]
            )
            self.NsPoints = []
            for point_idx in closest:
                self.NsPoints.append(points[point_idx])

        # Find iteration point for each centroid
        for _, point in self.NsPoints:
            self.zhs.append(self._update_zh(self.zh_prev, point))
            self.fh_lo = list(self.lower_bounds_factory.result(self.zh_prev))
            self.zh_los.append(self.fh_lo)

            if not self.problem.points:
                self.zh_reach = []
            else:
                self.zh_reach.append(
                    len(reachable_points(self.NsPoints, self.zh_los[-1], self.zhs[-1]))
                )
        self.current_iter -= 1
        return list(zip(self.zh_los, self.zhs))


class NAUTILUSv1(NAUTILUS):
    """
    The first NAUTILUS method variant[1]_

    References
    ----------

    [1] Miettinen, K.; Eskelinen, P.; Ruiz, F. & Luque, M.,
        NAUTILUS method: An interactive technique in multiobjective optimization based on the nadir point,
        European Journal of Operational Research, 2010 , 206 , 426-434.
    """

    def print_current_iteration(self):
        if self.current_iter == 0:
            print("Closeness: ", self.distance(self.zh, self.fh))
            print("Final iteration point:", self.zh)
        else:
            print(
                "Iteration %s/%s"
                % (self.user_iters - self.current_iter, self.user_iters)
            )
            print("Closeness: ", self.distance(self.zh, self.fh))
            print("Iteration point:", self.zh)
            print("Lower boundary:", self.fh_lo)
        print("==============================")

    def __init__(self, method, method_class):
        super().__init__(method, method_class)

    def _update_fh(self):
        self.fh = list(self.fh_factory.result(self.preference, self.zh_prev)[1])

    def next_iteration(self, preference=None):
        """
        Return next iteration bounds
        """
        if preference:
            self.preference = preference
            print(("Given preference: %s" % self.preference.pref_input))
        self._update_fh()

        # tmpzh = list(self.zh)
        self._update_zh(self.zh, self.fh)
        # self.zh = list(np.array(self.zh) / 2. + np.array(self.zh_prev) / 2.)
        # self.zh_prev = tmpzh
        if self.current_iter != 1:
            self.fh_lo = list(self.lower_bounds_factory.result(self.zh_prev))

        self.current_iter -= 1

        return self.fh_lo, self.zh


class NNAUTILUS(NAUTILUS):
    """
    NAVIGATOR NAUTILUS method

    Attributes
    ----------

    fh : list of floats
        Current non-dominated point

    zh : list of floats
        Current iteration point

    fh_up : list of floats
        Upper boundary for iteration points reachable from iteration point zh

    fh_lo : list of floats
        Lower boundary for iteration points reachable from iteration point  zh




    """

    class NegativeIntervalWarning(UnexpectedCondition):

        def __str__(self):
            return "Upper boundary is smaller than lower boundary"

    def __init__(self, method, method_class):
        super().__init__(method, method_class)
        self.current_iter = 100
        self.ref_point = None

        self.fh_up = None

    def _update_fh(self):
        u = [1.0] * len(self.ref_point)
        pref = DirectSpecification(self.problem, u, self.ref_point)
        self.fh = list(self.fh_factory.result(pref, self.zh_prev)[1])
        logging.debug("updated fh: %s", self.fh)

    def update_points(self):
        self.problem.points = reachable_points(
            self.problem.points, self.fh_lo, self.fh_up
        )

    def next_iteration(self, ref_point, bounds=None):
        """
        Calculate the next iteration point to be shown to the DM

        Parameters
        ----------
        ref_point : list of float
        Reference point given by the DM
        """
        if bounds:
            self.problem.points = reachable_points(
                self.problem.points, self.problem.ideal, bounds
            )
        if not utils.isin(self.fh, self.problem.points) or ref_point != self.ref_point:
            self.ref_point = list(ref_point)
            self._update_fh()

        self._update_zh(self.zh, self.fh)

        self.fh_lo = list(self.lower_bounds_factory.result(self.zh))
        self.fh_up = list(self.upper_bounds_factory.result(self.zh))

        logging.debug(f"Updated upper boundary: {self.fh_up}")
        logging.debug(f"Uppadet lower boundary: {self.fh_lo}")

        if not np.all(np.array(self.fh_up) > np.array(self.fh_lo)):
            warn(self.NegativeIntervalWarning())

        assert utils.isin(self.fh_up, self.problem.points)
        assert utils.isin(self.fh_lo, self.problem.points)

        dist = self.distance(self.zh, self.fh)

        # Reachable points
        self.update_points()

        lP = len(self.problem.points)
        self.current_iter -= 1

        return dist, self.fh, self.zh, self.fh_lo, self.fh_up, lP
