"""Tests related to the NAUTILUS Navigator method."""
import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm.nautilus_navigator import (
    calculate_navigation_point,
    calculate_distance_to_front,
    calculate_reachable_bounds,
    calculate_reachable_solution,
)
from desdeo.problem import zdt1, binh_and_korn, river_pollution_problem


@pytest.mark.nautilus_navigator
def test_calculate_navigation_point():
    """Tests the function to calculate a new navigation point."""
    previous_point = [2.5, -2.2, 3.3]  # previous navigation point
    reachable_objective_vector = [0.5, -1.1, 2.2]  # assumed min, max, min
    number_of_steps_remaining = 42

    nav_point = calculate_navigation_point(previous_point, reachable_objective_vector, number_of_steps_remaining)

    # the new navigation point should be closer to the reachable objective vector.
    assert np.linalg.norm(np.array(reachable_objective_vector) - np.array(nav_point)) < np.linalg.norm(
        np.array(reachable_objective_vector) - np.array(previous_point)
    )


@pytest.mark.nautilus_navigator
def test_calculate_distance_to_front():
    """Tests the calculation of the distance from a navigation point to the front."""
    reachable_objective_vector = [-2.2, 6.9, 420, 48]  # assumed min, min, max max
    nadir_point = [2.0, 20.1, 86.2, 18.1]

    farther_nav_point = [-0.1, 14.2, 220, 33.0]
    closer_nav_point = [-1.1, 7.2, 160, 29.2]

    distance_far = calculate_distance_to_front(farther_nav_point, reachable_objective_vector, nadir_point)
    distance_close = calculate_distance_to_front(closer_nav_point, reachable_objective_vector, nadir_point)

    # the distance from the farther point should be greater than from the closer one
    assert distance_far > distance_close


@pytest.mark.slow
@pytest.mark.nautilus_navigator
def test_calculate_reachable_solution():
    """Test the calculation of a new reachable solution."""
    problem = zdt1(10)
    obj_symbols = [objective.symbol for objective in problem.objectives]
    reference_point_1 = [0.8, 0.2]

    res_1 = calculate_reachable_solution(problem, reference_point_1)

    assert res_1.success

    objective_vector_1 = [res_1.optimal_objectives[key][0] for key in obj_symbols]

    reference_point_2 = [0.1, 0.8]

    res_2 = calculate_reachable_solution(problem, reference_point_2)

    assert res_2.success

    objective_vector_2 = [res_2.optimal_objectives[key][0] for key in obj_symbols]

    # the first objective vector computed should be closer to the first reference point
    # than the second and vice versa

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

    lower_bounds, upper_bounds = calculate_reachable_bounds(problem, nav_point)

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

    lower_bounds, upper_bounds = calculate_reachable_bounds(problem, nav_point)

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

    lower_bounds, upper_bounds = calculate_reachable_bounds(problem, nav_point)

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
