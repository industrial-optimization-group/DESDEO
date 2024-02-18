"""Tests related to the NAUTILUS Navigator method."""
import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm.nautilus_navigator import (
    calculate_navigation_point,
    calculate_distance_to_front,
    solve_reachable_bounds,
    solve_reachable_solution,
)
from desdeo.problem import zdt1, binh_and_korn, river_pollution_problem, objective_dict_to_numpy_array


@pytest.mark.nautilus_navigator
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


@pytest.mark.nautilus_navigator
def test_calculate_distance_to_front():
    """Tests the calculation of the distance from a navigation point to the front."""
    problem = river_pollution_problem()

    reachable_objective_vector = {"f_1": -5.01, "f_2": -3.0, "f_3": 5.1, "f_4": -5.9, "f_5": 0.11}

    farther_nav_point = {"f_1": -4.8, "f_2": -2.86, "f_3": 4.2, "f_4": -6.9, "f_5": 0.22}
    closer_nav_point = {"f_1": -4.9, "f_2": -2.9, "f_3": 4.8, "f_4": -6.1, "f_5": 0.19}

    distance_far = calculate_distance_to_front(problem, farther_nav_point, reachable_objective_vector)
    distance_close = calculate_distance_to_front(problem, closer_nav_point, reachable_objective_vector)

    # the distance from the closer point should be greater than from the farther one
    # (because 0 means we are farthest, and 100 means we are on the front.)
    assert distance_far < distance_close

    # from nadir point, distance should be zero
    distance_nadir = calculate_distance_to_front(
        problem, {objective.symbol: objective.nadir for objective in problem.objectives}, reachable_objective_vector
    )

    assert distance_nadir == 0

    # on the reachable solution, we are on the front and distanc should be 100
    distance_front = calculate_distance_to_front(problem, reachable_objective_vector, reachable_objective_vector)

    assert distance_front == 100


@pytest.mark.slow
@pytest.mark.nautilus_navigator
def test_calculate_reachable_solution():
    """Test the calculation of a new reachable solution."""
    problem = zdt1(10)
    obj_symbols = [objective.symbol for objective in problem.objectives]
    reference_point_1 = {"f_1": 0.8, "f_2": 0.2}

    res_1 = solve_reachable_solution(problem, reference_point_1)

    assert res_1.success

    objective_vector_1 = [res_1.optimal_objectives[key] for key in obj_symbols]

    reference_point_2 = {"f_1": 0.1, "f_2": 0.8}

    res_2 = solve_reachable_solution(problem, reference_point_2)

    assert res_2.success

    objective_vector_2 = [res_2.optimal_objectives[key] for key in obj_symbols]

    # the first objective vector computed should be closer to the first reference point
    # than the second and vice versa

    reference_point_1 = objective_dict_to_numpy_array(problem, reference_point_1)
    reference_point_2 = objective_dict_to_numpy_array(problem, reference_point_2)

    distance_1 = np.linalg.norm(np.array(reference_point_1) - np.array(objective_vector_1))
    distance_2 = np.linalg.norm(np.array(reference_point_1) - np.array(objective_vector_2))

    assert distance_1 < distance_2

    distance_1 = np.linalg.norm(np.array(reference_point_2) - np.array(objective_vector_1))
    distance_2 = np.linalg.norm(np.array(reference_point_2) - np.array(objective_vector_2))

    assert distance_2 < distance_1


@pytest.mark.nautilus_navigator
def test_calculate_reachable_bounds():
    """Test the calculation of reachable bounds."""
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
    # lower bound should be lower or equal to the nav point for max objective
    assert lower_bounds["f_2"] <= nav_point["f_2"]

    # upper bound should be less than or equel to nav point for min objective
    assert upper_bounds["f_1"] <= nav_point["f_1"]
    # upper bound should be higher (better) than nav point for max objective
    assert upper_bounds["f_2"] > nav_point["f_2"]

    # check than bounds make sense
    for symbol in [objective.symbol for objective in problem.objectives]:
        assert upper_bounds[symbol] > lower_bounds[symbol]


@pytest.mark.slow
@pytest.mark.nautilus_navigator
def test_calculate_reachable_bounds_complicated():
    """Test calcualte reachable bounds with more objectivs."""
    # more objectives, both min and max
    problem = river_pollution_problem()

    nav_point = {"f_1": -5.25, "f_2": -3.1, "f_3": 4.2, "f_4": -6.9, "f_5": 0.22}

    lower_bounds, upper_bounds = solve_reachable_bounds(problem, nav_point)

    # lower bound should be lower (better) than the navigation point, for min objectives
    assert lower_bounds["f_1"] < nav_point["f_1"]
    assert lower_bounds["f_2"] < nav_point["f_2"]
    assert lower_bounds["f_5"] < nav_point["f_5"]
    # lower bound should be lower or equal to the nav point for max objectives
    assert lower_bounds["f_3"] <= nav_point["f_3"]
    assert lower_bounds["f_4"] <= nav_point["f_4"]

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
