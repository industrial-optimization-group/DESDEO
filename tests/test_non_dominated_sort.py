"""Tests related to non-dominated sorting."""

import numpy as np
import numpy.testing as npt

from desdeo.tools.non_dominated_sorting import fast_non_dominated_sort


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
