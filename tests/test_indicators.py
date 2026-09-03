"""Tests for indicators."""

from itertools import product
from math import factorial

import moocore
import numpy as np
import pytest
from pymoo.indicators.igd_plus import IGDPlus
from pymoo.util.ref_dirs import get_reference_directions
from scipy.special import gamma

from desdeo.tools.indicators_binary import epsilon_component, epsilon_indicator
from desdeo.tools.indicators_unary import (
    distance_indicators,
    hv,
    hv_batch,
    igd_plus_batch,
    igd_plus_indicator,
    r2_batch,
    r2_indicator,
    r_metric_indicators_batch,
)


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
    obj = 3
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
    assert hv_vals["internal"][0] > hv_vals["uniform"][0] > hv_vals["boundary"][0], (
        "Internal HV is not highest at nadir"
    )
    # At 2* nadir, Uniform should be highest
    assert hv_vals["uniform"][1] > hv_vals["boundary"][1] > hv_vals["internal"][1], (
        "Uniform HV is not highest at 2*nadir"
    )
    # At 10* nadir, Boundary should be highest
    assert hv_vals["boundary"][2] > hv_vals["uniform"][2] > hv_vals["internal"][2], (
        "Boundary HV is not highest at 10*nadir"
    )


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
@pytest.mark.parametrize("p", [1.0, 2.0, 3.0])
def test_distance_indicators_against_moocore(p):
    """Check IGD and the averaged Hausdorff distance against moocore's reference implementation."""
    obj = 3
    ref_set = get_reference_directions("energy", obj, n_points=200)
    rng = np.random.default_rng(42)
    solution_set = ref_set[rng.choice(ref_set.shape[0], size=60, replace=False)] + rng.normal(0, 0.02, (60, obj))

    inds = distance_indicators(solution_set, ref_set, p=p)

    assert np.isclose(inds.igd, moocore.igd(solution_set, ref=ref_set)), "IGD does not match moocore"
    assert np.isclose(inds.ahd, moocore.avg_hausdorff_dist(solution_set, ref_set, p=p)), (
        f"AHD does not match moocore for p={p}"
    )


@pytest.mark.indicators
def test_distance_indicators_p_semantics():
    """IGD_p/GD_p must be power means, and thus insensitive to the cardinality of an equally-spread set."""
    ref_set = np.column_stack([np.linspace(0, 1, 100), 1 - np.linspace(0, 1, 100)])

    # p == 1 reduces the generalized mean to the arithmetic mean, so IGD_p == IGD and GD_p == GD.
    inds = distance_indicators(ref_set[::4], ref_set, p=1.0)
    assert np.isclose(inds.igd_p, inds.igd), "IGD_p is not IGD at p=1"
    assert np.isclose(inds.gd_p, inds.gd), "GD_p is not GD at p=1"

    # p == inf reduces the generalized mean to the maximum distance.
    inds_inf = distance_indicators(ref_set[::4], ref_set, p=np.inf)
    assert inds_inf.igd_p >= inds.igd_p, "IGD_inf should not be below IGD_1"
    assert np.isfinite(inds_inf.ahd), "AHD is not finite for p=inf"

    # Sampling the same front more densely must not inflate GD_p.
    gd_ps = []
    for num_points in [50, 200, 800]:
        t = np.linspace(0, 1, num_points)
        gd_ps.append(distance_indicators(np.column_stack([t, 1 - t]), ref_set, p=2.0).gd_p)
    assert max(gd_ps) < 0.02, f"GD_p scales with the cardinality of the solution set: {gd_ps}"

    for bad_p in [0.0, -1.0]:
        with pytest.raises(ValueError, match="must be positive"):
            distance_indicators(ref_set[::4], ref_set, p=bad_p)


@pytest.mark.indicators
def test_igd_plus():
    """Test the IGD+ indicator."""
    num_full_points = 500
    obj = 3
    ref_set = get_reference_directions("energy", obj, n_points=num_full_points)
    subset = ref_set[0:250, :]

    igd_plus_result = igd_plus_indicator(subset, ref_set)

    assert isinstance(igd_plus_result.igd_plus, float), "IGD+ is not a float"
    assert igd_plus_result.igd_plus >= 0, "IGD+ is negative"
    assert np.allclose(igd_plus_result.igd_plus, igd_plus_result.igd_plus), "IGD+ result is NaN"


@pytest.mark.indicators
def test_igd_plus_batch():
    """Test the IGD+ indicator batch function."""
    num_full_points = 500
    obj = 3
    ref_set = get_reference_directions("energy", obj, n_points=num_full_points)
    subset1 = ref_set[0:100, :]
    subset2 = ref_set[100:250, :]

    solution_sets = {"subset1": subset1, "subset2": subset2}
    igd_plus_batch_result = igd_plus_batch(solution_sets, ref_set)

    assert isinstance(igd_plus_batch_result, dict), "Result is not a dictionary"
    assert "subset1" in igd_plus_batch_result and "subset2" in igd_plus_batch_result, "Missing subsets in results"

    for set_name, igd_plus_indicators in igd_plus_batch_result.items():
        assert isinstance(igd_plus_indicators.igd_plus, float), f"IGD+ for {set_name} is not a float"
        assert igd_plus_indicators.igd_plus >= 0, f"IGD+ for {set_name} is negative"
        assert np.allclose(igd_plus_indicators.igd_plus, igd_plus_indicators.igd_plus), f"IGD+ for {set_name} is NaN"

    # Validate results with pymoo's IGD+
    for set_name, igd_plus_indicators in igd_plus_batch_result.items():
        pymoo_igd_plus = IGDPlus(ref_set).do(solution_sets[set_name])
        assert np.isclose(igd_plus_indicators.igd_plus, pymoo_igd_plus, atol=1e-6), (
            f"IGD+ for {set_name} does not match pymoo's result"
        )


@pytest.mark.indicators
def test_r_metric_calculator_batch():
    """Test the R-metric calculator batch function."""
    num_full_points = 500
    obj = 3
    ref_points = get_reference_directions("energy", obj, n_points=num_full_points)
    subset1 = ref_points[0:100, :]
    subset2 = ref_points[100:250, :]

    solution_sets = {"subset1": subset1, "subset2": subset2}
    r_metrics_batch = r_metric_indicators_batch(solution_set=solution_sets, ref_points=ref_points)

    assert isinstance(r_metrics_batch, dict), "Result is not a dictionary"
    assert "subset1" in r_metrics_batch and "subset2" in r_metrics_batch, "Missing subsets in results"

    for set_name, r_metrics in r_metrics_batch.items():
        assert isinstance(r_metrics.r_hv, float), f"R-HV for {set_name} is not a float"
        assert isinstance(r_metrics.r_igd, float), f"R-IGD for {set_name} is not a float"
        assert r_metrics.r_hv >= 0, f"R-HV for {set_name} is negative"
        assert np.allclose(r_metrics.r_igd, r_metrics.r_igd), "R-IGD is not close to itself"  # non NaN values


@pytest.mark.indicators
def test_r2_batch_with_ref_dirs():
    """Test the R2 batch function using structured reference directions."""
    num_full_points = 500
    obj = 3
    ref_set = get_reference_directions("energy", obj, n_points=num_full_points)
    subset1 = ref_set[0:100, :]
    subset2 = ref_set[100:250, :]

    solution_sets = {"subset1": subset1, "subset2": subset2}
    lambda_set = get_reference_directions("energy", obj, n_points=100)
    z_star = np.min(ref_set, axis=0)

    r2_results = r2_batch(solution_sets, lambda_set, z_star)

    assert isinstance(r2_results, dict), "R2 batch output is not a dictionary"
    assert "subset1" in r2_results and "subset2" in r2_results, "Subset keys missing in R2 batch result"

    for name, result in r2_results.items():
        assert isinstance(result.r2_value, float), f"{name}'s R2 value is not a float"
        assert result.r2_value < 0, f"{name}'s R2 value should be negative"
        assert np.isfinite(result.r2_value), f"{name}'s R2 value is not finite"


@pytest.mark.indicators
def test_r2_is_a_utility_so_higher_is_better():
    """R2 here is the utility form: a better set must score HIGHER, and every value is negative.

    This is the opposite orientation to every other indicator in the module, and it is the single
    thing about R2 that gets misread -- treated as lower-is-better it inverts an entire ranking, with
    no error and no NaN to give it away. The docstrings say so; this makes the sign a test failure
    rather than a reading-comprehension exercise.
    """
    rng = np.random.default_rng(0)
    objectives = 3
    lambda_set = get_reference_directions("energy", objectives, n_points=50)
    z_star = np.zeros(objectives)

    good = np.abs(rng.normal(size=(40, objectives))) * 0.3 + 0.2
    # Strictly dominated by `good`, componentwise, so there is no argument about which set is better.
    worse = good + 0.5

    better_score = r2_indicator(good, lambda_set, z_star).r2_value
    worse_score = r2_indicator(worse, lambda_set, z_star).r2_value

    assert better_score > worse_score, "R2 is a utility: the dominating set must score higher"
    assert better_score < 0, "the augmented Tchebycheff utility is negative away from the ideal point"


@pytest.mark.indicators
def test_r2_negates_the_distance_form_other_frameworks_report():
    """DESDEO's R2 is exactly minus the minimisation-form R2 that PlatEMO and jMetal print.

    Both conventions are in the literature and they differ by a sign, so anyone comparing a DESDEO
    number against a published one needs to know which is which. Pinned as an equality rather than
    described in prose, so the relationship cannot drift.
    """
    rng = np.random.default_rng(1)
    objectives = 3
    lambda_set = get_reference_directions("energy", objectives, n_points=40)
    z_star = np.zeros(objectives)
    solution_set = np.abs(rng.normal(size=(30, objectives))) * 0.4 + 0.1
    rho = 0.05

    # The distance form: mean over weights of the smallest augmented Tchebycheff distance.
    distances = np.abs(z_star - solution_set)
    per_weight = [np.min(np.max(weights * distances, axis=1) + rho * distances.sum(axis=1)) for weights in lambda_set]
    distance_form = float(np.mean(per_weight))

    assert r2_indicator(solution_set, lambda_set, z_star, rho).r2_value == pytest.approx(-distance_form)


@pytest.mark.indicators
def test_epsilon_component():
    """Test the per-objective epsilon component between two solutions."""
    s1 = np.array([0.3, 0.1, 0.5])
    s2 = np.array([0.5, 0.2, 0.6])
    assert epsilon_component(s1, s1) == 0, f"Epsilon for identical vectors is {epsilon_component(s1, s2)}, should be 0"
    assert np.isclose(epsilon_component(s1, s1 - 0.1), 0.1), "epsilon should be the amount that a vector is shifted"
    assert epsilon_component(s1, s2) == 0, "I_eps({s1}, s{2}) should be 0, as s1 is not worse than s2 in any component"
    assert epsilon_component(s2, s1) == 0.2, "I_eps({s2}, s{1}) should be 0.2"


@pytest.mark.indicators
def test_epsilon_indicator():
    """Test the epsilon indicator for two sets."""
    rng = np.random.default_rng(0)
    set1 = rng.random((100, 3))
    set2 = rng.random((100, 3))

    ei1 = epsilon_indicator(set1, set2, kind="additive")
    ei2 = np.array([[epsilon_component(s1, s2) for s1 in set1] for s2 in set2]).min(axis=1).max()

    assert np.isclose(ei1, ei2), (
        f"Epsilon indicator results do not match: {ei1} vs {ei2} between our and moocore implementations"
    )
