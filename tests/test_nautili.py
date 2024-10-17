"""Tests related to the NAUTILI method."""

import numpy as np
import pytest
from fixtures import dtlz2_5x_3f_data_based  # noqa: F401

from desdeo.mcdm.nautili import (
    solve_reachable_bounds,
    solve_reachable_solution,
)
from desdeo.problem import (
    binh_and_korn,
    objective_dict_to_numpy_array,
    river_pollution_problem,
)


@pytest.mark.slow
@pytest.mark.nautili
def test_solve_reachable_solution():
    """Test the solving of a new reachable solution."""
    problem = binh_and_korn()
    prev_nav_point = {"f_1": 80.0, "f_2": 30.0}
    group_improvement_direction = {"f_1": 50, "f_2": 30}

    res_1 = solve_reachable_solution(problem, group_improvement_direction, prev_nav_point)

    assert res_1.success

    objective_vector_1 = objective_dict_to_numpy_array(problem, res_1.optimal_objectives)

    group_improvement_direction_2 = {"f_1": 25, "f_2": 50}

    res_2 = solve_reachable_solution(problem, group_improvement_direction_2, prev_nav_point)

    assert res_2.success

    objective_vector_2 = objective_dict_to_numpy_array(problem, res_2.optimal_objectives)

    # the first objective vector computed should be closer to the first reference point
    # than the second and vice versa

    group_improvement_direction = objective_dict_to_numpy_array(problem, group_improvement_direction)
    group_improvement_direction_2 = objective_dict_to_numpy_array(problem, group_improvement_direction_2)

    distance_1 = np.linalg.norm(group_improvement_direction - objective_vector_1)
    distance_2 = np.linalg.norm(group_improvement_direction - objective_vector_2)

    assert distance_1 < distance_2

    distance_1 = np.linalg.norm(group_improvement_direction - objective_vector_1)
    distance_2 = np.linalg.norm(group_improvement_direction - objective_vector_2)

    assert distance_2 < distance_1


@pytest.mark.nautili
def test_solve_reachable_solution_discrete(dtlz2_5x_3f_data_based):  # noqa: F811
    """Tests the solving of the reachable solution with a fully discrete problem."""
    # TODO: fix namings and make cip smarter
    problem = dtlz2_5x_3f_data_based

    prev_nav_point = {"f1": 1.0, "f2": 1.0, "f3": 1.0}
    reference_point_1 = {"f1": 0.8, "f2": 0.8, "f3": 0.01}  # group improvement direction

    res_1 = solve_reachable_solution(problem, reference_point_1, prev_nav_point)

    assert res_1.success

    objective_vector_1 = objective_dict_to_numpy_array(problem, res_1.optimal_objectives)

    reference_point_2 = {"f1": 0.05, "f2": 0.02, "f3": 0.98}  # group improvement direction

    res_2 = solve_reachable_solution(problem, reference_point_2, prev_nav_point)

    assert res_2.success

    objective_vector_2 = objective_dict_to_numpy_array(problem, res_2.optimal_objectives)

    reference_point_1 = objective_dict_to_numpy_array(problem, reference_point_1)
    reference_point_2 = objective_dict_to_numpy_array(problem, reference_point_2)

    distance_1 = np.linalg.norm(reference_point_1 - objective_vector_1)
    distance_2 = np.linalg.norm(reference_point_1 - objective_vector_2)

    assert distance_1 < distance_2

    distance_1 = np.linalg.norm(reference_point_2 - objective_vector_1)
    distance_2 = np.linalg.norm(reference_point_2 - objective_vector_2)

    assert distance_2 < distance_1


@pytest.mark.slow
@pytest.mark.nautili
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


@pytest.mark.nautili
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
@pytest.mark.nautili
def test_solve_reachable_bounds_complicated():
    """Test solving of the reachable bounds with more objectivs."""
    # more objectives, both min and max
    problem = river_pollution_problem()

    nav_point = {"f_1": -5.25, "f_2": -3.1, "f_3": 4.2, "f_4": -6.9, "f_5": 0.22}

    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    # lower bound should be lower (better) than the navigation point, for min objectives
    assert lower_bounds["f_1"] < nav_point["f_1"]
    assert lower_bounds["f_2"] < nav_point["f_2"]
    assert lower_bounds["f_5"] < nav_point["f_5"]
    # lower bound should be higher or equal to the nav point for max objectives
    assert lower_bounds["f_3"] >= nav_point["f_3"]
    assert lower_bounds["f_4"] >= nav_point["f_4"]

    # upper bound should be less than or equel to nav point min objectives
    assert upper_bounds["f_1"] <= nav_point["f_1"]
    assert upper_bounds["f_2"] <= nav_point["f_2"]
    assert upper_bounds["f_5"] <= nav_point["f_5"]

    # upper bound should be higher (better) than nav point for max objectives
    assert upper_bounds["f_3"] > nav_point["f_3"]
    assert upper_bounds["f_4"] > nav_point["f_4"]

    # check than bounds make sense
    for symbol in [objective.symbol for objective in problem.objectives]:
        assert upper_bounds[symbol] > lower_bounds[symbol]


@pytest.mark.slow
@pytest.mark.nautili
def test_nautili_aggregation():
    """TODO: Test nautili aggregation aggregation"""
