"""Tests related to the reference point method."""

import numpy as np
import numpy.testing as npt
import pytest
from scipy.spatial.distance import pdist

from desdeo.mcdm import rpm_solve_solutions, rpm_intermediate_solutions
from desdeo.problem import objective_dict_to_numpy_array
from desdeo.problem.testproblems import dtlz2, river_pollution_problem


@pytest.mark.rpm
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


@pytest.mark.rpm
@pytest.mark.slow
def test_rpm_solve_solutions_discontinuous():
    """Test the solve function with a discontinuous problem."""
    problem = river_pollution_problem()

    reference_point = {"f_1": -6, "f_2": -3, "f_3": 7, "f_4": 0.5, "f_5": 0.05}

    results = rpm_solve_solutions(problem, reference_point)


@pytest.mark.rpm
def test_rpm_intermediate_solutions_continuous():
    """Test the solve function with a continuous problem."""
    n_variables = 6
    n_objectives = 3
    num_desired = 1

    problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)

    reference_point_close1 = {"f_1": 0.55, "f_2": 0.0, "f_3": 0.36}
    reference_point_close2 = {"f_1": 0.95, "f_2": 1.0, "f_3": 0.30}
    reference_point_far1 = {"f_1": 0.95, "f_2": 0.83, "f_3": 0.90}
    reference_point_far2 = {"f_1": 0.85, "f_2": 0.77, "f_3": 0.96}

    results_close = rpm_intermediate_solutions(problem, reference_point_close1, reference_point_close2, num_desired)
    results_far = rpm_intermediate_solutions(problem, reference_point_far1, reference_point_far2, num_desired)

    assert len(results_close) == num_desired
    assert len(results_far) == num_desired

    # all solutions should be Pareto optimal
    for res in results_close:
        for var_symbol in ["x_3", "x_4", "x_5", "x_6"]:
            npt.assert_allclose(res.optimal_variables[var_symbol], 0.5)

    for res in results_far:
        for var_symbol in ["x_3", "x_4", "x_5", "x_6"]:
            npt.assert_allclose(res.optimal_variables[var_symbol], 0.5)


@pytest.mark.rpm
@pytest.mark.slow
def test_rpm_intermediate_solutions_discontinuous():
    """Test the solve function with a discontinuous problem."""
    problem = river_pollution_problem()

    reference_point1 = {"f_1": -8, "f_2": -3, "f_3": 8, "f_4": 1, "f_5": 0.04}
    reference_point2 = {"f_1": -4, "f_2": -3, "f_3": 6, "f_4": 0, "f_5": 0.06}

    results = rpm_intermediate_solutions(problem, reference_point1, reference_point2, num_desired=2)
