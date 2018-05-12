# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016  Vesa Ojalehto
"""
Module description
"""

import abc

import numpy as np


class OptimizationProblem(object, metaclass=abc.ABCMeta):
    """
    Single objective optimization problem


    Attributes
    ----------
    problem : OptimizationMethod instance
        Method used for solving the problem

    """

    def __init__(self, method):
        """
        Constructor
        """
        self.nconst = 0
        self.problem = method

    def evaluate(self, objectives):
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
    def _evaluate(self, objectives):
        pass


class ScalarizedProblem(OptimizationProblem, metaclass=abc.ABCMeta):

    def __init__(self, method, **kwargs):
        super(ScalarizedProblem, self).__init__(method)
        self.reference = None
        self._preferences = None
        self.weights = None

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

    @abc.abstractmethod
    def _evaluate(self, objectives):
        pass


class AchievementProblem(ScalarizedProblem):
    r"""
    Finds new solution by solving achievement scalarizing function[1]_

    .. math::

       \mbox{minimize}
           & \displaystyle{
               \max_{i=1, \dots , k}
               \left\{\, \mu_i(f_i(\mathbf x) - q_i)\ \right\}}
           + \rho \sum_{i=1}^k \mu_i (f_i(\mathbf x)- q_i) \\
       \mbox{subject to}
           & {\bf{x}} \in S

    References
    ----------

    [1] A. P. Wierzbicki, The use of reference objectives in multiobjective optimization, in: G. Fandel, T. Gal (Eds.),
    Multiple Criteria Decision Making, Theory and Applications, Vol. 177 of Lecture Notes in Economics and Mathematical Systems,
    Springer, 1980, pp. 468-486.
    """

    def __init__(self, method, **kwargs):
        super(AchievementProblem, self).__init__(method, **kwargs)
        self.eps = kwargs.get("eps", 0.00001)
        self.rho = kwargs.get("rho", 0.01)

        self.scaling_weights = list(
            1.0
            / (np.array(self.problem.nadir) - (np.array(self.problem.ideal) - self.eps))
        )
        self.weights = [1.0] * len(self.problem.nadir)

        self.v_ach = np.vectorize(lambda f, w, r: w * (f - r))

    def _set_preferences(self):
        self.scaling_weights = list(
            1.0
            / (np.array(self.problem.nadir) - (np.array(self.problem.ideal) - self.eps))
        )

    def _augmentation(self, objectives):
        """Calculate augmentation term
        """

        rho = self.v_ach(objectives, np.array(self.scaling_weights), self.reference)
        return np.sum(rho, axis=1) * self.rho

    def _ach(self, objectives):
        return self.v_ach(
            objectives,
            np.array(self.scaling_weights) * np.array(self.weights),
            self.reference,
        )

    def _evaluate(self, objectives):
        rho = self._augmentation(objectives)
        v_ach = self._ach(objectives)

        # Calculate maximum of the values for each objective
        ach = np.max(v_ach, axis=1)
        return ach + rho, []


class NIMBUSProblem(AchievementProblem):
    """
    Finds new solution by solving NIMBUS scalarizing function[1]_
    """

    def __init__(self, method, **kwargs):
        super(NIMBUSProblem, self).__init__(method, **kwargs)
        self.raug = kwargs.get("raug", 0.001)

    def _set_preference(self, preference):
        self.weights = [1.0] * len(self.problem.nadir)

    def _evaluate(self, objectives):
        fid_a = self._preferences.with_class("<") + self._preferences.with_class("<=")
        ach = self._ach(objectives)
        v_obj = ach[:, fid_a]

        obj = np.max(v_obj, axis=1)

        rho = self._augmentation(objectives)

        fid_e = fid_a + self._preferences.with_class("=")

        # Bounds
        fid_b = self._preferences.with_class(">=")
        self.nconst = len(fid_e + fid_b)

        bounds = []
        for fid in fid_b:
            bounds.append(np.array(objectives)[:, fid] - self._preferences[fid][1])
        for fid in fid_e:
            bounds.append(np.array(objectives)[:, fid])
        return obj + rho, bounds


class EpsilonConstraintProblem(OptimizationProblem):
    r"""
    Solves epsilon constraint problem

    .. math::

        \mbox{minimize}
            & f_r({\bf{x}}) \\
        \mbox{subject to}
            & f_j({\bf{x}}) \le z _j, j = 1, \dots, k, j \neq r, \\
            & {\bf{x}} \in S, \\

    Attributes
    ----------
    bounds : List of numerical values
        Boundary value for the each of the objectives. The objective with boundary of None is to be minimized


    """

    def __init__(self, method, obj_bounds=None):
        super(EpsilonConstraintProblem, self).__init__(method)
        self.obj_bounds = obj_bounds
        self.objective = 100000

    def _evaluate(self, objectives):
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

        return objs, np.transpose(consts)
