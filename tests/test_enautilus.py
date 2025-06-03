"""Tests related to the NAUTILUS method."""

import numpy as np
import numpy.testing as npt
import pytest
from fixtures import dtlz2_5x_3f_data_based  # noqa: F401

from desdeo.mcdm.enautilus import calculate_intermediate_points, calculate_reachable_subset, prune_by_average_linkage
from desdeo.mcdm.nautili import solve_reachable_bounds
from desdeo.mcdm.nautilus import (
    calculate_navigation_point,
    points_to_weights,
    ranks_to_weights,
    solve_reachable_solution,
)
from desdeo.problem import objective_dict_to_numpy_array
from desdeo.problem.testproblems import binh_and_korn, river_pollution_problem


@pytest.mark.enautilus
def test_pruning():
    """Test the prune_by_average_linkage_method."""
    cluster1 = np.array([[0.0, 0.0], [0.1, 0.1], [0.2, 0.0], [0.0, 0.2], [0.1, 0.2]])
    cluster2 = np.array([[10.0, 10.0], [10.1, 10.2], [9.9, 10.1], [10.2, 9.9], [9.8, 9.9]])
    points = np.vstack((cluster1, cluster2))

    # Prune to 2 representative points
    pruned = prune_by_average_linkage(points, k=2)

    assert pruned.shape == (2, 2)
    # Should be close to one point from each cluster
    assert any(np.linalg.norm(p - [0.1, 0.1]) < 0.3 for p in pruned)
    assert any(np.linalg.norm(p - [10.0, 10.0]) < 0.3 for p in pruned)


@pytest.mark.enautilus
def test_calculate_intermediate_points():
    """Test that intermediate points are calculated correctly."""
    z_prev = np.array([2.0, 4.0])
    zs_reps = np.array([[6.0, 8.0], [10.0, 12.0]])
    iterations_left = 2

    expected = np.array(
        [
            [4.0, 6.0],  # (1/2)*z_prev + (1/2)*[6,8]
            [6.0, 8.0],  # (1/2)*z_prev + (1/2)*[10,12]
        ]
    )

    result = calculate_intermediate_points(z_prev, zs_reps, iterations_left)

    assert result.shape == expected.shape
    np.testing.assert_allclose(result, expected)


@pytest.mark.enautilus
def test_calculate_reachable_subset():
    """Tests that the reachable subset is calculated in a sane way."""
    non_dominated = np.array(
        [
            [1.0, 1.0],  # too small
            [2.0, 2.0],  # on lower bound
            [2.5, 2.5],  # inside bounds
            [3.0, 3.0],  # on upper bound
            [3.5, 3.5],  # too large
            [2.0, 3.1],  # out of bounds (second objective too high)
            [1.9, 2.9],  # out of bounds (first objective too low)
        ]
    )

    lower_bounds = np.array([2.0, 2.0])
    z_preferred = np.array([3.0, 3.0])

    expected = np.array([[2.0, 2.0], [2.5, 2.5], [3.0, 3.0]])

    result = calculate_reachable_subset(non_dominated, lower_bounds, z_preferred)

    assert result.shape == expected.shape
    assert set(map(tuple, result)) == set(map(tuple, expected))
