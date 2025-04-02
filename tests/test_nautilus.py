"""Tests related to the NAUTILUS method."""

import numpy as np
import numpy.testing as npt
import pytest
from fixtures import dtlz2_5x_3f_data_based  # noqa: F401

from desdeo.mcdm.nautili import solve_reachable_bounds
from desdeo.mcdm.nautilus import (
    calculate_navigation_point,
    points_to_weights,
    ranks_to_weights,
    solve_reachable_solution,
)
from desdeo.problem import objective_dict_to_numpy_array
from desdeo.problem.testproblems import binh_and_korn, river_pollution_problem


@pytest.mark.nautilus
def test_calculate_navigation_point():
    """Tests the function to calculate a new navigation point."""
    problem = river_pollution_problem()
    previous_point = {"f_1": -5.01, "f_2": -3.0, "f_3": 4.2, "f_4": -6.9, "f_5": 0.22}
    reachable_objective_vector = {"f_1": -5.25, "f_2": -3.1, "f_3": 5.1, "f_4": -5.9, "f_5": 0.12}
    number_of_steps_remaining = 42

    nav_point = calculate_navigation_point(
        problem, previous_point, reachable_objective_vector, number_of_steps_remaining
    )

    # transform to numpy arrays for easier comparison
    nav_point = objective_dict_to_numpy_array(problem, nav_point)
    reachable_objective_vector = objective_dict_to_numpy_array(problem, reachable_objective_vector)
    previous_point = objective_dict_to_numpy_array(problem, previous_point)

    # the new navigation point should be closer to the reachable objective vector.
    d_nav_to_reachale = np.linalg.norm(reachable_objective_vector - nav_point)
    d_prev_to_reachable = np.linalg.norm(reachable_objective_vector - previous_point)

    assert d_nav_to_reachale < d_prev_to_reachable

    # the navigation point should also be between the previous navigation point and the reachable solution
    d_prev_to_nav = np.linalg.norm(nav_point - previous_point)

    # previous_point <--------> reachable == previous_point <---> nav_point <----> reachable
    npt.assert_almost_equal(d_prev_to_reachable, d_nav_to_reachale + d_prev_to_nav)


@pytest.mark.slow
@pytest.mark.nautilus
def test_solve_reachable_solution():
    """Test the solving of a new reachable solution."""
    problem = binh_and_korn()
    prev_nav_point = {"f_1": 80.0, "f_2": 30.0}
    ranks = {"f_1": 1, "f_2": 2}
    weights = ranks_to_weights(ranks, problem)

    res_1 = solve_reachable_solution(problem, weights, prev_nav_point)

    assert res_1.success

    ranks = {"f_1": 2, "f_2": 1}
    weights = ranks_to_weights(ranks, problem)

    res_2 = solve_reachable_solution(problem, weights, prev_nav_point)

    assert res_2.success

    # the first solution should attain a better value for the second objective
    assert res_1.optimal_objectives["f_2"] < res_2.optimal_objectives["f_2"]

    # the second solution should attain a better value for the first objective
    assert res_2.optimal_objectives["f_1"] < res_1.optimal_objectives["f_1"]


@pytest.mark.nautilus
def test_solve_reachable_solution_discrete(dtlz2_5x_3f_data_based):  # noqa: F811
    """Tests the solving of the reachable solution with a fully discrete problem."""
    problem = dtlz2_5x_3f_data_based

    prev_nav_point = {"f1": 1.0, "f2": 1.0, "f3": 1.0}
    points = {"f1": 30, "f2": 50, "f3": 20}
    weights = points_to_weights(points, problem)

    res_1 = solve_reachable_solution(problem, weights, prev_nav_point)

    assert res_1.success

    points = {"f1": 90, "f2": 2, "f3": 8}
    weights = points_to_weights(points, problem)

    res_2 = solve_reachable_solution(problem, weights, prev_nav_point)

    assert res_2.success

    # the first solution should attain a better value for the second objective
    assert res_1.optimal_objectives["f2"] < res_2.optimal_objectives["f2"]

    # the second solution should attain a better value for the first objective
    assert res_2.optimal_objectives["f1"] < res_1.optimal_objectives["f1"]


@pytest.mark.slow
@pytest.mark.nautilus
def test_solve_reachable_bounds():
    """Test the solving of reachable bounds."""
    # Two objectives, both min
    problem = binh_and_korn(maximize=(False, False))

    nav_point = {"f_1": 60.0, "f_2": 20.1}

    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    # lower bound should be lower (better) than the navigation point, for both
    assert lower_bounds["f_1"] < nav_point["f_1"]
    assert lower_bounds["f_2"] < nav_point["f_2"]

    # upper bound should be less than or equel to nav point, for both
    assert upper_bounds["f_1"] <= nav_point["f_1"]
    assert upper_bounds["f_2"] <= nav_point["f_2"]

    # check than bounds make sense
    for symbol in [objective.symbol for objective in problem.objectives]:
        assert upper_bounds[symbol] > lower_bounds[symbol]

    # Two objectives, min and max
    problem = binh_and_korn(maximize=(False, True))  # min max

    nav_point = {"f_1": 60.0, "f_2": -20.1}

    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    # lower bound should be lower (better) than the navigation point for min objective
    assert lower_bounds["f_1"] < nav_point["f_1"]
    # lower bound should be higher or equal to the nav point for max objective
    assert lower_bounds["f_2"] >= nav_point["f_2"]

    # upper bound should be less than or equel to nav point for min objective
    assert upper_bounds["f_1"] <= nav_point["f_1"]
    # upper bound should be higher (better) than nav point for max objective
    assert upper_bounds["f_2"] > nav_point["f_2"]

    # check than bounds make sense
    for symbol in [objective.symbol for objective in problem.objectives]:
        assert upper_bounds[symbol] > lower_bounds[symbol]


@pytest.mark.nautilus
def test_solve_reachable_bounds_discrete(dtlz2_5x_3f_data_based):  # noqa: F811
    """Test the solving of reachable bounds with a discrete problem."""
    # Two objectives, both min
    problem = dtlz2_5x_3f_data_based

    nav_point = {"f1": 0.65, "f2": 0.85, "f3": 0.75}

    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    # lower bound should be lower (better) than the navigation point
    assert all(lower_bounds[objective.symbol] < nav_point[objective.symbol] for objective in problem.objectives)

    # upper bound should be less than or equel to nav point, for both
    assert all(upper_bounds[objective.symbol] <= nav_point[objective.symbol] for objective in problem.objectives)

    # check than bounds make sense
    for symbol in [objective.symbol for objective in problem.objectives]:
        assert upper_bounds[symbol] > lower_bounds[symbol]


@pytest.mark.slow
@pytest.mark.nautilus
def test_solve_reachable_bounds_complicated():
    """Test solving of the reachable bounds with more objectivs."""
    # more objectives, both min and max
    problem = river_pollution_problem()

    nav_point = {"f_1": -5.25, "f_2": -3.1, "f_3": 4.2, "f_4": -6.9, "f_5": 0.22}

    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    # lower bound should be lower (better) than the navigation point, for min objectives
    assert lower_bounds["f_5"] < nav_point["f_5"]
    # lower bound should be higher or equal to the nav point for max objectives
    assert lower_bounds["f_1"] >= nav_point["f_1"]
    assert lower_bounds["f_2"] >= nav_point["f_2"]
    assert lower_bounds["f_3"] >= nav_point["f_3"]
    assert lower_bounds["f_4"] >= nav_point["f_4"]

    # upper bound should be less than or equel to nav point min objectives
    assert upper_bounds["f_5"] <= nav_point["f_5"]

    # upper bound should be higher (better) than nav point for max objectives
    assert upper_bounds["f_1"] > nav_point["f_1"]
    assert upper_bounds["f_2"] > nav_point["f_2"]
    assert upper_bounds["f_3"] > nav_point["f_3"]
    assert upper_bounds["f_4"] > nav_point["f_4"]

    # check than bounds make sense
    for symbol in [objective.symbol for objective in problem.objectives]:
        assert upper_bounds[symbol] > lower_bounds[symbol]
