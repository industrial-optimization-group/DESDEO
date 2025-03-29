"""Tests for indicators."""

from itertools import product
from math import factorial

import numpy as np
import pandas as pd
import pytest
from pymoo.util.ref_dirs import get_reference_directions
from scipy.special import gamma

from desdeo.tools.indicators_unary import distance_indicators, distance_indicators_batch, hv, hv_batch, PHI, PhiDecision


@pytest.mark.indicators
@pytest.mark.parametrize("obj, shape", list(product([2, 3, 4], ["simplex", "sphere", "inv_simplex", "inv_sphere"])))
def test_hv(obj, shape):
    """Test the hypervolume indicator for different PF shapes, dimensions, and densities."""
    num_points = [50, 100, 500]
    if shape == "simplex":
        true_hv = 1 - (1 / factorial(obj))
    elif shape == "sphere":
        sphere_volume = (np.pi ** (obj / 2)) / (gamma(obj / 2 + 1))
        true_hv = 1 - (1 / 2**obj) * sphere_volume
    elif shape == "inv_simplex":
        true_hv = 1 / factorial(obj)
    elif shape == "inv_sphere":
        sphere_volume = (np.pi ** (obj / 2)) / (gamma(obj / 2 + 1))
        true_hv = 1 / 2**obj * sphere_volume
    volumes = []
    for points in num_points:
        ref_dirs = get_reference_directions("energy", obj, n_points=points)
        if shape == "sphere":
            ref_dirs /= np.linalg.norm(ref_dirs, axis=1)[:, None]
        elif shape == "inv_sphere":
            ref_dirs /= np.linalg.norm(ref_dirs, axis=1)[:, None]
            ref_dirs = 1 - ref_dirs
        elif shape == "inv_simplex":
            ref_dirs = 1 - ref_dirs
        volumes.append(hv(ref_dirs, 1))
    assert volumes[0] < volumes[1] < volumes[2], f"Volumes are not increasing for denser fronts for {shape} {obj}D"
    assert (
        volumes[2] < true_hv < volumes[2] * 2  # HV differences are too large for, e.g., allclose.
    ), f"Volume is not correct for {shape} {obj}D, expected {true_hv} got {volumes[2]}, at {num_points[2]} points"


@pytest.mark.indicators
def test_hv_batch():
    """Test the hypervolume indicator for a batch of PFs."""
    num_full_points = 500
    distribution = ["uniform", "internal", "boundary"]
    obj = 3
    true_hv = 1 - (1 / factorial(obj))
    rp_components = [1.0, 2.0, 10.0]
    ref_dirs = get_reference_directions("energy", obj, n_points=num_full_points)
    set_boundary = 1 - ref_dirs
    set_boundary = set_boundary[set_boundary.max(axis=1) > 0.9]
    num_points = set_boundary.shape[0]
    ref_dirs = get_reference_directions("energy", obj, n_points=num_points)
    set_uniform = 1 - ref_dirs
    set_internal = ref_dirs * 0.95 + 0.05 / 3
    set_internal = 1 - set_internal

    solution_sets = {"uniform": set_uniform, "internal": set_internal, "boundary": set_boundary}
    hv_vals = hv_batch(solution_sets, rp_components)

    # At nadir, HV internal should be highest
    assert (
        hv_vals["internal"][0] > hv_vals["uniform"][0] > hv_vals["boundary"][0]
    ), "Internal HV is not highest at nadir"
    # At 2* nadir, Uniform should be highest
    assert (
        hv_vals["uniform"][1] > hv_vals["boundary"][1] > hv_vals["internal"][1]
    ), "Uniform HV is not highest at 2*nadir"
    # At 10* nadir, Boundary should be highest
    assert (
        hv_vals["boundary"][2] > hv_vals["uniform"][2] > hv_vals["internal"][2]
    ), "Boundary HV is not highest at 10*nadir"


@pytest.mark.indicators
def test_distance_indicators():
    """Test the distance indicators for a batch of PFs."""
    num_full_points = 500
    obj = 3
    set_uniform = get_reference_directions("energy", obj, n_points=num_full_points)
    subset = set_uniform[0:250, :]

    distance_inds = distance_indicators(subset, set_uniform)

    assert np.allclose(distance_inds.gd, 0), "GD is not 0 for a subset"

    assert np.allclose(distance_inds.gd_p, 0), "GD_p is not 0 for a subset"

    assert distance_inds.igd > 0, "IGD is not positive for a subset"

    assert distance_inds.igd_p > 0, "IGD_p is not positive for a subset"

    assert distance_inds.ahd == distance_inds.igd_p, "AHD is not equal to IGD_p for a subset"


@pytest.mark.indicators
def test_get_phi():
    solution_set = np.array([[0.2, 0.3], [0.4, 0.5], [0.6, 0.7]])
    reference_point = np.array([0.5, 0.5])
    nadir = np.array([1.0, 1.0])
    ideal = np.array([0.0, 0.0])

    phi_instance = PHI(solution_set, reference_point, nadir, ideal)
    print(type(phi_instance))
    dominated, metric_vals = phi_instance.get_phi()

    assert dominated
    assert metric_vals != [0, 0, 0, 0]


@pytest.mark.indicators
def test_assess_decision_phase():
    indicator_values = (0.5, 0.6, 0.7, 0.8)
    nadir = np.array([1.0, 1.0])

    set_of_RPs = np.array([[0.2, 0.3], [0.4, 0.5], [0.6, 0.7]])
    main_RP = np.array([0.5, 0.5])

    decision_instance = PhiDecision(indicator_values, nadir)
    result, weights = decision_instance.assess_decision_phase(set_of_RPs, main_RP)

    assert isinstance(result, float), "assess_decision_phase() should return a float value as result."
    assert isinstance(weights, np.ndarray), "Weights should be a numpy array."
