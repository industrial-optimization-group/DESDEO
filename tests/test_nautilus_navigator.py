"""Tests related to the NAUTILUS Navigator method."""
import numpy as np
import numpy.testing as npt
import pytest

from desdeo.mcdm.nautilus_navigator import calculate_navigation_point


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
