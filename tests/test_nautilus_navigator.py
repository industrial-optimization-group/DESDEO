"""Tests related to the NAUTILUS Navigator method."""
import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm.nautilus_navigator import calculate_navigation_point, calculate_distance_to_front


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
