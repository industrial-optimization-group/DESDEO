"""Tests for indicators."""

from math import factorial

import numpy as np
import pytest
from pymoo.util.ref_dirs import get_reference_directions
from scipy.special import gamma

from desdeo.tools.indicators_unary import distance_indicators, distance_indicators_batch, hv, hv_batch


@pytest.mark.indicators
def test_hv():
    """Test the hypervolume indicator."""
    num_points = [100, 1000, 10000]
    num_objectives = [2, 3, 4]
    shapes = ["planar", "sphere"]
    for obj in num_objectives:
        for shape in shapes:
            if shape == "planar":
                true_hv = 1 - (1 / factorial(obj))
            else:
                sphere_volume = (np.pi ** (obj / 2)) / (gamma(obj / 2 + 1))
                true_hv = 1 - (1 / 2**obj) * sphere_volume
            volumes = []
            for points in num_points:
                print(shape, obj)
                ref_dirs = get_reference_directions("energy", obj, n_points=points)
                if shape == "sphere":
                    ref_dirs /= np.linalg.norm(ref_dirs, axis=1)[:, None]
                volumes.append(hv(ref_dirs, 1))
            assert (
                volumes[0] < volumes[1] < volumes[2]
            ), f"Volumes are not increasing for dense points for {shape} {obj}D"
            assert (
                pytest.approx(true_hv, abs=1e-2) == volumes[2]
            ), f"Volume is not correct for {shape} {obj}D, expected {true_hv} got {volumes[2]}"
