"""
Contains tools to estimate the range of objective values in the Patero optimal
set. The vector with the best objective values is called the ideal, and the
vector with the worst values is called the nadir.
"""

from typing import List, Tuple, Type

import numpy as np

from desdeo.optimization.OptimizationMethod import OptimizationMethod
from desdeo.optimization.OptimizationProblem import SelectedOptimizationProblem
from desdeo.problem.Problem import MOProblem


def estimate_payoff_table(
    opt_meth_cls: Type[OptimizationMethod], mo_prob: MOProblem
) -> Tuple[List[float], List[float]]:
    """
    Estimates the ideal and nadir by using a payoff table. This should give a
    good estimate for the ideal, but can be very inaccurate for the nadir. For an explanation of why, see [1]_.

    References
    ----------

    [1] Deb, K., Miettinen, K., & Chaudhuri, S. (2010).
    Toward an estimation of nadir objective vector using a hybrid of evolutionary and local search approaches.
    IEEE Transactions on Evolutionary Computation, 14(6), 821-841.
    """
    ideal = [float("inf")] * mo_prob.nobj
    nadir = [float("-inf")] * mo_prob.nobj
    for i in range(mo_prob.nobj):
        meth = opt_meth_cls(SelectedOptimizationProblem(mo_prob, i))
        _decis, obj = meth.search()
        for j, obj_val in enumerate(obj):
            if obj_val < ideal[j]:
                ideal[j] = obj_val
            if obj_val > nadir[j]:
                nadir[j] = obj_val
    return ideal, nadir


def pad(idnad: Tuple[List[float], List[float]], pad_nadir=0.05, pad_ideal=0.0):
    """
    Pad an ideal/nadir estimate. This is mainly useful for padding the nadir
    estimated by a payoff table for safety purposes.
    """
    ideal, nadir = idnad
    ideal_arr = np.array(ideal)
    nadir_arr = np.array(nadir)
    idnad_range = nadir_arr - ideal_arr
    nadir_arr += pad_nadir * idnad_range
    ideal_arr -= pad_ideal * idnad_range
    return list(ideal_arr), list(nadir_arr)


def round_off(idnad: Tuple[List[float], List[float]], dp: int = 2):
    """
    Round off an ideal/nadir estimate e.g. so that it's looks nicer when
    plotted. This function is careful to round so only ever move the values
    away from the contained range.
    """
    ideal, nadir = idnad
    mult = np.power(10, dp)
    ideal_arr = np.floor(np.array(ideal) * mult) / mult
    nadir_arr = np.ceil(np.array(nadir) * mult) / mult
    return list(ideal_arr), list(nadir_arr)


def default_estimate(
    opt_meth: Type[OptimizationMethod], mo_prob: MOProblem, dp: int = 2
) -> Tuple[List[float], List[float]]:
    """
    The recommended nadir/ideal estimator - use a payoff table and then round
    off the result.
    """
    return round_off(estimate_payoff_table(opt_meth, mo_prob), dp)
