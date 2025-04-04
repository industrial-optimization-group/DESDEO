"""Tests related to the utility functions in the explanations module."""

import numpy as np
import pytest

from desdeo.explanations import generate_biased_mean_data


@pytest.mark.explanation_utils
def test_generate_biased_mean_data():
    """Tests that the generation of data with a biased mean works as intended."""
    data = np.array(
        [
            [1, 1, 1, 1],
            [2, 2, 2, 2],
            [3, 3, 3, 3],
            [4, 4, 4, 4],
            [5, 5, 5, 5],
            [6, 6, 6, 6],
            [7, 7, 7, 7],
            [8, 8, 8, 8],
            [9, 9, 9, 9],
        ]
    )

    targets = np.array([4.5, 4.5, 4.5, 4.5])
    min_size = 5
    max_size = 7

    subset_indices = generate_biased_mean_data(data, targets, min_size=min_size, max_size=max_size)

    assert len(subset_indices) >= min_size
    assert len(subset_indices) <= max_size

    assert np.isclose(data[subset_indices].mean(axis=0), targets).all()

    # change mean and sizes
    targets = np.array([1.5, 1.5, 1.5, 1.5])
    min_size = 2
    max_size = 3

    subset_indices = generate_biased_mean_data(data, targets, min_size=min_size, max_size=max_size)

    assert len(subset_indices) >= min_size
    assert len(subset_indices) <= max_size

    assert np.isclose(data[subset_indices].mean(axis=0), targets).all()


@pytest.mark.explanation_utils
def test_generate_biased_mean_data_1d():
    """Tests that the generation of data with a biased mean works as intended when data has a single column."""
    data = np.array(
        [
            [1],
            [2],
            [3],
            [4],
            [5],
            [6],
            [7],
            [8],
            [9],
        ]
    )

    targets = np.array([8.5])
    min_size = 2
    max_size = 6

    subset_indices = generate_biased_mean_data(data, targets, min_size=min_size, max_size=max_size)

    assert len(subset_indices) >= min_size
    assert len(subset_indices) <= max_size

    assert np.isclose(data[subset_indices].mean(axis=0), targets).all()
