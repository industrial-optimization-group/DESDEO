"""Tests related to the NAUTILUS method."""

import numpy as np
import pytest

from desdeo.mcdm.enautilus import (
    calculate_closeness,
    calculate_intermediate_points,
    calculate_lower_bounds,
    calculate_reachable_subset,
    prune_by_average_linkage,
)


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


def test_calculate_lower_bounds():
    """Test that calculate_lower_bounds works as expected."""
    nd_points = np.array(
        [
            [1.0, 2.0, 9.0],
            [0.5, 3.0, 6.0],
            [2.0, 1.5, 5.0],  # This one will be included only for f1
            [1.5, 2.5, 4.0],
        ]
    )
    z_intermediate = np.array([1.6, 2.6, 6.5])

    # Expected:
    # For f0 (min f0 s.t. f1, f2 ≤ 2.6, 6.5):
    #   feasible: [0.5, 3.0, 6.0] (fails f1), [1.5, 2.5, 4.0] -> min f0 = 1.5
    #
    # For f1 (min f1 s.t. f0, f2 ≤ 1.6, 6.5):
    #   feasible: [0.5, 3.0, 6.0], [1.5, 2.5, 4.0] -> min f1 = 2.5
    #
    # For f2 (min f2 s.t. f0, f1 ≤ 1.6, 2.6):
    #   feasible: [1.0, 2.0, 9.0] (too high), [1.5, 2.5, 4.0] -> min f2 = 4.0

    expected = np.array([1.5, 2.5, 4.0])
    result = calculate_lower_bounds(nd_points, z_intermediate)

    assert result.shape == expected.shape
    np.testing.assert_allclose(result, expected)


@pytest.mark.enautilus
def test_calculate_closeness():
    """Tests that the closeness is calculated correctly."""
    z_nadir = np.array([0.0, 0.0])
    z_rep = np.array([4.0, 0.0])

    # Case 1: halfway: expect 50.0
    z_half = np.array([2.0, 0.0])
    result_half = calculate_closeness(z_half, z_nadir, z_rep)
    np.testing.assert_allclose(result_half, 50.0)

    # Case 2: same as nadir: expect 0.0
    z_same_as_nadir = z_nadir
    result_nadir = calculate_closeness(z_same_as_nadir, z_nadir, z_rep)
    np.testing.assert_allclose(result_nadir, 0.0)

    # Case 3: same as representative: expect 100.0
    z_same_as_rep = z_rep
    result_rep = calculate_closeness(z_same_as_rep, z_nadir, z_rep)
    np.testing.assert_allclose(result_rep, 100.0)
