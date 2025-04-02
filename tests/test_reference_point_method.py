"""Tests related to the reference point method."""

import numpy as np
import numpy.testing as npt
import pytest
from scipy.spatial.distance import pdist

from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import objective_dict_to_numpy_array
from desdeo.problem.testproblems import dtlz2, river_pollution_problem


@pytest.mark.rmp
def test_rpm_solve_solutions_continuous():
    """Test the solve function with a continuous problem."""
    n_variables = 6
    n_objectives = 3

    problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)

    reference_point_close = {"f_1": 0.75, "f_2": 0.50, "f_3": 0.33}
    reference_point_far = {"f_1": 0.9, "f_2": 0.80, "f_3": 0.93}

    results_close = rpm_solve_solutions(problem, reference_point_close)
    results_far = rpm_solve_solutions(problem, reference_point_far)

    assert len(results_close) == n_objectives + 1
    assert len(results_far) == n_objectives + 1

    # all solutions should be Pareto optimal
    for res in results_close:
        for var_symbol in ["x_3", "x_4", "x_5", "x_6"]:
            npt.assert_allclose(res.optimal_variables[var_symbol], 0.5)

    for res in results_far:
        for var_symbol in ["x_3", "x_4", "x_5", "x_6"]:
            npt.assert_allclose(res.optimal_variables[var_symbol], 0.5)

    # the objective vectors of the solution computed with the close reference
    # point should be less spread out than the solution with the farther
    # reference point.

    pairwise_distances_close = pdist(
        [objective_dict_to_numpy_array(problem, res.optimal_objectives) for res in results_close], metric="euclidean"
    )

    pairwise_distances_far = pdist(
        [objective_dict_to_numpy_array(problem, res.optimal_objectives) for res in results_far], metric="euclidean"
    )

    assert np.mean(pairwise_distances_far) > np.mean(pairwise_distances_close)


@pytest.mark.rmp
@pytest.mark.slow
def test_rpm_solve_solutions_discontinuous():
    """Test the solve function with a discontinuous problem."""
    problem = river_pollution_problem()

    reference_point = {"f_1": -6, "f_2": -3, "f_3": 7, "f_4": 0.5, "f_5": 0.05}

    results = rpm_solve_solutions(problem, reference_point)
