"""Tests related to the NAUTILUS method."""

import numpy as np
import numpy.testing as npt
import pytest
from fixtures import dtlz2_5x_3f_data_based  # noqa: F401

from desdeo.mcdm.enautilus import prune_by_average_linkage
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
