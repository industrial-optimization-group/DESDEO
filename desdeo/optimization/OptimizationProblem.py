# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
This module contains single objective optimization problems. Principally there
are scalarization functions for converting multi-objective problems into
single-objective functions.
"""

import abc
from functools import reduce
from typing import (  # noqa - rm when pyflakes understands type hints
    Any,
    List,
    Optional,
    Tuple,
)

import numpy as np

from desdeo.problem.Problem import MOProblem
from desdeo.utils.exceptions import PreferenceUndefinedError


class OptimizationProblem(object, metaclass=abc.ABCMeta):
    """
    Single objective optimization problem


    Attributes
    ----------
    problem
        The multi-objective problem that the single-objective problem is posed
        in terms of

    """

    def __init__(self, mo_problem: MOProblem) -> None:
        """
        Constructor
        """
        self.nconst = 0
        self.problem = mo_problem

    def evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        """
        Evaluate value of the objective function and possible additional constraints


        Parameters
        ----------

        objectives : list of objective values

        Returns
        -------
        objective : list of floats
            Objective function values corresponding to objectives
        constraint : 2-D matrix of floats
            Constraint function values corresponding to objectives per row. None if no constraints are added
        """
        return self._evaluate(objectives)

    @abc.abstractmethod
    def _evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        pass


class SelectedOptimizationProblem(OptimizationProblem):
    """
    Converts a multi-objective optimization problem to a single-objective one
    by selecting only a single objective.
    """

    def __init__(self, mo_problem: MOProblem, n: int) -> None:
        """
        Parameters
        ----------

        n
            The index of the objective to be considered
        """
        super().__init__(mo_problem)
        self.n = n

    def _evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        return [objectives[0][self.n]], None


class ScalarizedProblem(OptimizationProblem, metaclass=abc.ABCMeta):

    def __init__(self, mo_problem: MOProblem, **kwargs) -> None:
        super(ScalarizedProblem, self).__init__(mo_problem)
        self.reference = None
        self._preferences = None  # type: Any
        self.weights = None  # type: Optional[List[float]]

    @abc.abstractmethod
    def _set_preferences(self):
        pass

    def set_preferences(self, preference, last_solution):
        self._preferences = preference
        try:
            self.reference = self._preferences.reference_point()
        except AttributeError:
            self.reference = last_solution
        self.weights = self._preferences.weights()
        self._set_preferences()

    def evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        if self._preferences is None:
            raise PreferenceUndefinedError(
                "Attempted to evaluate scalarizing function before preferences have "
                "been set."
            )
        return super().evaluate(objectives)

    @abc.abstractmethod
    def _evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        pass


v_ach = np.vectorize(lambda f, w, r: w * (f - r))
v_pen = np.vectorize(lambda f, w, r: w * f)


class AchievementProblemBase(ScalarizedProblem):
    r"""
    Solves problems of the form:

    .. math::

       & \mbox{minimize}\ \
           & \displaystyle{
               \max_{i=1, \dots , k}
               \left\{\, \mu_i(\dots) \right\}}
           + \rho \sum_{i=1}^k \mu_i (\dots) \\
       & \mbox{subject to}\
           & {\bf{x}} \in S

    This is an abstract base class. Implementors should override `_ach`, `_augmentation` and
    `_set_scaling_weights`.
    """

    def __init__(self, mo_problem: MOProblem, **kwargs) -> None:
        self.eps = kwargs.get("eps", 0.00001)
        self.rho = kwargs.get("rho", 0.01)
        kwargs.get("rho", 0.01)

        super().__init__(mo_problem, **kwargs)

    def _set_preferences(self):
        self._set_scaling_weights()

    @abc.abstractmethod
    def _ach(self, objectives: List[List[float]]) -> List[float]:
        """
        Calculate achievement term
        """
        pass

    @abc.abstractmethod
    def _augmentation(self, objectives: List[List[float]]) -> List[float]:
        """
        Calculate augmentation term
        """
        pass

    def _evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        v_aug = self._augmentation(objectives)
        v_ach = self._ach(objectives)

        # Calculate maximum of the values for each objective
        ach = np.max(v_ach, axis=1)
        aug = np.sum(v_aug, axis=1) * self.rho
        return ach + aug, None

    @abc.abstractmethod
    def _set_scaling_weights(self):
        pass


class SimpleAchievementProblem(AchievementProblemBase):
    r"""
    Solves a simple form of achievement scalarizing function

    .. math::

       & \mbox{minimize}\ \
           & \displaystyle{
               \max_{i=1, \dots , k}
               \left\{\, \mu_i(f_i(\mathbf x) - q_i)\ \right\}}
           + \rho \sum_{i=1}^k \mu_i (f_i(\mathbf x)) \\
       & \mbox{subject to}\
           & {\bf{x}} \in S

    If ach_pen=True is passed to the constructor, the full achivement function
    is used as the penatly, causing us to instead solve[1]_

    .. math::

       & \mbox{minimize}\ \
           & \displaystyle{
               \max_{i=1, \dots , k}
               \left\{\, \mu_i(f_i(\mathbf x) - q_i)\ \right\}}
           + \rho \sum_{i=1}^k \mu_i (f_i(\mathbf x)- q_i) \\
       & \mbox{subject to}\
           & {\bf{x}} \in S

    This is an abstract base class. Implementors should override `_get_rel` and
    `_set_scaling_weights`.

    References
    ----------

    [1] A. P. Wierzbicki, The use of reference objectives in multiobjective optimization, in: G. Fandel, T. Gal (Eds.),
    Multiple Criteria Decision Making, Theory and Applications, Vol. 177 of Lecture Notes in Economics and Mathematical Systems,
    Springer, 1980, pp. 468-486.
    """

    def __init__(self, mo_problem: MOProblem, **kwargs) -> None:
        self.scaling_weights = None
        super().__init__(mo_problem, **kwargs)
        self.weights = [1.0] * self.problem.nobj
        if kwargs.get("ach_pen"):
            self.v_pen = v_ach
        else:
            self.v_pen = v_pen

    def _ach(self, objectives: List[List[float]]) -> List[float]:
        assert self.scaling_weights is not None
        return v_ach(objectives, np.array(self.scaling_weights), self._get_rel())

    def _augmentation(self, objectives: List[List[float]]) -> List[float]:
        assert self.scaling_weights is not None
        return self.v_pen(objectives, np.array(self.scaling_weights), self._get_rel())

    @abc.abstractmethod
    def _get_rel(self):
        pass


class NIMBUSStomProblem(SimpleAchievementProblem):
    r"""
    Finds new solution by solving NIMBUS version of the satisficing trade-off
    method (STOM).

    .. math::

        & \mbox{minimize }\ \  &  \displaystyle{ \max_{i=1, \dots , k} \left\lbrack\,
        \frac{f_i(\mathbf x) - z_i^{\star\star}}{\bar{z}_i - z_i^{\star\star}}
        \, \right\rbrack} +
        \rho \sum_{i=1}^k
        \frac{f_i(\mathbf x)}{\bar z_i - z_i^{\star\star}}  \\
        &\mbox{subject to }\ &\mathbf x \in S

    """

    def _set_scaling_weights(self):
        r"""
        Set scaling weights to:

        .. math::

            \frac{1}{\bar z_i - z_i^{\star\star}}

        """
        self.scaling_weights = (
            1.0 / (np.array(self.reference) - (np.array(self.problem.ideal) - self.eps))
        )

    def _get_rel(self):
        return np.array(self.problem.ideal) - self.eps


class NIMBUSGuessProblem(SimpleAchievementProblem):
    r"""
    Finds new solution by solving NIMBUS version of the GUESS method.

    .. math::

        & \mbox{minimize }\ \  & \displaystyle{\max_{i \notin I^{\diamond}}}
            \left\lbrack \frac{f_i(\mathbf x) -
            z_i^{\mathrm{nad}}}{z_i^{\mathrm{nad}}- \bar z_i} \right\rbrack  +
        \rho \sum_{i=1}^k
        \frac{f_i(\mathbf x)}{z_i^{\mathrm{nad}}-\bar z_i} \\
        &\mbox{subject to }\ &\mathbf x \in S.

    In this implementation :math:`z^\mathrm{nad}` is `eps` larger than the true nadir
    to protect against the case where :math:`\bar z_i = z_i^{\mathrm{nad}}` causing
    division by zero.
    """

    def _set_scaling_weights(self):
        r"""
        Set scaling weights to:

        .. math::

            \frac{1}{z_i^{\mathrm{nad}}-\bar z_i}

        """
        self.scaling_weights = (
            1.0 / (np.array(self.problem.nadir) + self.eps - np.array(self.reference))
        )

    def _get_rel(self):
        return np.array(self.problem.nadir)


class NadirStarStarScaleMixin:
    r"""
    This mixin implements `_set_scaling_weights` as:

    .. math::

        \frac{1}{z_i^{\mathrm{nad}} - z_i^{\star\star}}

    """

    def _set_scaling_weights(self):
        self.scaling_weights = (
            1.0
            / (np.array(self.problem.nadir) - (np.array(self.problem.ideal) - self.eps))
        )


class NIMBUSAchievementProblem(NadirStarStarScaleMixin, SimpleAchievementProblem):
    r"""
    Finds new solution by solving NIMBUS version of the achivement problem.

    .. math::
        & \mbox{minimize }\ \  & \displaystyle{\max_{i=1, \dots , k}\left\lbrack\,
        \frac{f_i(\mathbf x) - \bar z_i}{z_i^{\mathrm{nad}}-z^{\star\star}_i}\,
        \right\rbrack} +
        \rho \sum_{i=1}^k
        \frac{f_i(\mathbf x) }{z_i^{\mathrm{nad}}-z^{\star\star}_i}
          \\
        &\mbox{subject to }\ &\mathbf x \in S.

    """

    def _get_rel(self):
        return self.reference


class NIMBUSProblem(NadirStarStarScaleMixin, SimpleAchievementProblem):
    r"""
    Finds new solution by solving NIMBUS scalarizing function.

    .. math::

        & \mbox{minimize }\ \  & \displaystyle{\max_{{i\in I^<}\atop{j \in I^{\le}}}
            \left [ \frac{f_i(\mathbf x) - z^{\star}_i}
        {z_i^{\mathrm{nad}}-z^{\star\star}_i},
            \frac{f_j(\mathbf x) - \hat{z}_j }{z_j^{\mathrm{nad}}-z^{\star\star}_j}
             \right ] + \rho \sum_{i=1}^k
        \frac{f_i(\mathbf x)}{z_i^{\mathrm{nad}}-z^{\star\star}_i}}  \\
        & \mbox{subject to }\  &f_i(\mathbf x) \le f_i(\mathbf x^c) \ \mbox{ for all
            } \ \ i \in     I^< \cup I^{\le} \cup I^=, \\
        && f_i(\mathbf x) \le \varepsilon_i  \ \mbox{ for all } \  i \in I^{\ge},  \\
        && \mathbf x \in S

    """

    def __init__(self, mo_problem: MOProblem, **kwargs) -> None:
        super().__init__(mo_problem, **kwargs)

    def _ach(self, objectives):
        fid_a = self._preferences.with_class("<") + self._preferences.with_class("<=")
        ach = super()._ach(objectives)
        v_obj = ach[:, fid_a]
        return v_obj

    def _get_rel(self):
        return self.reference

    def _evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        obj, no_bounds = super()._evaluate(objectives)
        assert no_bounds is None

        # Bounds
        fid_e = reduce(
            lambda a, b: a + b,
            (self._preferences.with_class(x) for x in ["<", "<=", "="]),
        )
        fid_b = self._preferences.with_class(">=")
        self.nconst = len(fid_e + fid_b)

        bounds_lists = []
        for fid in fid_b:
            bounds_lists.append(
                np.array(objectives)[:, fid] - self._preferences[fid][1]
            )
        for fid in fid_e:
            bounds_lists.append(np.array(objectives)[:, fid])
        bounds = np.rot90(bounds_lists)
        return obj, bounds


class NautilusAchievementProblem(NadirStarStarScaleMixin, SimpleAchievementProblem):
    r"""
    Solves problems of the form:

    .. math::

       & \mbox{minimize}\ \
           & \displaystyle{
               \max_{i=1, \dots , k}
               \left\{\, \mu_i(f_i(\mathbf x) - q_i)\ \right\}}
           + \rho \sum_{i=1}^k \frac{f_i(\mathbf x) - q_i}
               {z_i^{\mathrm{nad}}-z^{\star\star}_i} \\
       & \mbox{subject to}\
           & {\bf{x}} \in S

    """

    def _ach(self, objectives):
        return self.weights * (np.array(objectives) - self.reference)

    def _get_rel(self):
        return self.reference


class EpsilonConstraintProblem(OptimizationProblem):
    r"""
    Epsilon constraint problem

    .. math::

        & \mbox{minimize}\ \
            & f_r({\bf{x}}) \\
        & \mbox{subject to}\
            & f_j({\bf{x}}) \le z _j, j = 1, \dots, k, j \neq r, \\
            & {\bf{x}} \in S, \\

    Attributes
    ----------
    bounds : List of numerical values
        Boundary value for the each of the objectives. The objective with boundary of None is to be minimized


    """

    def __init__(self, mo_problem: MOProblem, obj_bounds=None) -> None:
        super(EpsilonConstraintProblem, self).__init__(mo_problem)
        self.obj_bounds = obj_bounds
        self.objective = 100000

        self._coeff = 1

    def _evaluate(
        self, objectives: List[List[float]]
    ) -> Tuple[List[float], Optional[np.ndarray]]:
        objs = []
        consts = []
        for ind in objectives:
            const = []
            for oi, obj in enumerate(self.obj_bounds):
                if obj:
                    const.append(ind[oi] - obj)
                else:
                    fi = oi
            objs.append(ind[fi])
            consts.append(const)

        return np.array(objs) * self._coeff, np.array(consts)


class MaxEpsilonConstraintProblem(EpsilonConstraintProblem):
    r"""
    Epsilon constraint problem where the objective is to be maximized

    .. math::

        & \mbox{maximize}\ \
            & f_r({\bf{x}}) \\
        & \mbox{subject to}\
            &f_j({\bf{x}}) \le z _j, j = 1, \dots, k, j \neq r, \\
            & {\bf{x}} \in S

    This is a special case of using epsilon constraint, to be very clear
    when using maximized scalarizing function.

    Attributes
    ----------
    bounds : List of numerical values
        Boundary value for the each of the objectives. The objective with boundary of None is to be minimized


    """

    def __init__(self, mo_problem: MOProblem, obj_bounds=None) -> None:
        super().__init__(mo_problem)
        # Note that a class is needed, but here we
        # wish to be clear of our intention
        self._coeff = -1
