"""Tests related to non-dominated sorting."""

import numpy as np
import numpy.testing as npt

from desdeo.tools.non_dominated_sorting import dominance_matrix, fast_non_dominated_sort


def test_simple():
    """Simple tests to check that fast non-dominated sorting works as intended."""
    # Should result in three fronts
    three_fronts = np.array(
        [
            [1, 2, 3],
            [3, 1, 2],
            [2, 3, 1],
            [10, 20, 30],
            [30, 10, 20],
            [20, 30, 10],
            [100, 200, 300],
            [300, 100, 200],
            [200, 300, 100],
        ]
    )

    fronts = fast_non_dominated_sort(three_fronts)

    assert len(fronts) == 3
    npt.assert_equal(
        fronts,
        np.array(
            [
                [*(3 * [True]), *(6 * [False])],
                [*(3 * [False]), *(3 * [True]), *(3 * [False])],
                [*(6 * [False]), *(3 * [True])],
            ]
        ),
    )

    # Should result in one front
    one_front = np.array(
        [
            [1, 2, 3],
            [3, 1, 2],
            [2, 3, 1],
        ]
    )

    fronts = fast_non_dominated_sort(one_front)

    assert len(fronts) == 1
    npt.assert_equal(fronts, [3 * [True]])

    # Should result in 5 fronts (one for each solution)
    five_fronts = np.array([[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4], [5, 5, 5]])

    fronts = fast_non_dominated_sort(five_fronts)

    assert len(fronts) == 5
    npt.assert_equal(
        fronts,
        np.array(
            [
                [True, False, False, False, False],
                [False, True, False, False, False],
                [False, False, True, False, False],
                [False, False, False, True, False],
                [False, False, False, False, True],
            ]
        ),
    )


def test_dominance_matrix():
    """Element (i, j) of the dominance matrix is true exactly when solution i dominates solution j."""
    rng = np.random.default_rng(0)
    # Integer objectives so that ties, duplicates and weak dominance all occur.
    data = rng.integers(0, 4, size=(40, 3)).astype(float)

    matrix = dominance_matrix(data)

    no_worse = np.all(data[:, None, :] <= data[None, :, :], axis=2)
    better = np.any(data[:, None, :] < data[None, :, :], axis=2)
    npt.assert_equal(matrix, no_worse & better)
    assert not matrix.diagonal().any()
    assert dominance_matrix(np.empty((0, 3))).shape == (0, 0)
