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
from desdeo.problem import zdt1


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
