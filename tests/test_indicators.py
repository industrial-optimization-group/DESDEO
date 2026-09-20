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
    d_phi_batch,
    d_phi_indicator,
    desirability_values,
    distance_indicators,
    hv,
    hv_batch,
    igd_plus_batch,
    igd_plus_indicator,
    phi_plus_batch,
    phi_plus_indicator,
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


@pytest.mark.indicators
def test_desirability_values():
    """Test that the desirability function interpolates between, and stays within, its limits."""
    aspiration = np.array([0.2, 0.3])
    reservation = np.array([0.6, 0.5])
    c1, c2, epsilon_a, epsilon_r = 1.0, 0.0, 0.2, 0.2

    at_levels = desirability_values(np.array([aspiration, reservation]), aspiration, reservation, c1=c1, c2=c2)
    assert np.allclose(at_levels[0], c1), "The aspiration levels are not mapped to c1"
    assert np.allclose(at_levels[1], c2), "The reservation levels are not mapped to c2"

    midpoint = desirability_values((aspiration + reservation) / 2, aspiration, reservation, c1=c1, c2=c2)
    assert np.allclose(midpoint, (c1 + c2) / 2), "The desirability function is not linear between the levels"

    extremes = desirability_values(np.array([[-1e6, -1e6], [1e6, 1e6]]), aspiration, reservation, c1=c1, c2=c2)
    assert np.all(extremes[0] < c1 + epsilon_a), "The desirability function exceeds its upper limit"
    assert np.all(extremes[1] > c2 - epsilon_r), "The desirability function falls below its lower limit"
    assert np.allclose(extremes[0], c1 + epsilon_a, atol=1e-3), "The upper limit is not approached"
    assert np.allclose(extremes[1], c2 - epsilon_r, atol=1e-3), "The lower limit is not approached"

    # The desirability function is strictly decreasing, since the objectives are minimized.
    grid = np.linspace(-1, 2, 200)[:, np.newaxis] * np.ones(2)
    assert np.all(np.diff(desirability_values(grid, aspiration, reservation), axis=0) < 0), (
        "The desirability function is not strictly decreasing"
    )


@pytest.mark.indicators
def test_d_phi_indicator():
    """Test D-PHI and CI on solution sets with known indicator values."""
    aspiration = np.array([0.2, 0.2])
    reservation = np.array([0.6, 0.6])

    # A solution at the aspiration point has a desirability of (c1, c1) = (1, 1), and the reference point of the
    # hypervolume is (c2 - epsilon_r, c2 - epsilon_r) = (-0.2, -0.2), so D-PHI is 1.2 * 1.2.
    at_aspiration = d_phi_indicator(aspiration[np.newaxis, :], aspiration, reservation)
    assert np.isclose(at_aspiration.d_phi, 1.2**2), "D-PHI is not correct at the aspiration point"
    assert np.isclose(at_aspiration.ci, 0.0), "CI is not 0 at the aspiration point"

    # A solution at the reservation point has a desirability of (c2, c2) = (0, 0), so D-PHI is 0.2 * 0.2.
    at_reservation = d_phi_indicator(reservation[np.newaxis, :], aspiration, reservation)
    assert np.isclose(at_reservation.d_phi, 0.2**2), "D-PHI is not correct at the reservation point"
    assert at_reservation.ci < 0, "CI is not negative for a solution reaching no aspiration level"

    # Reaching every aspiration level is exactly what makes CI non-negative.
    assert d_phi_indicator(np.array([[0.1, 0.2]]), aspiration, reservation).ci >= 0, (
        "CI is negative for a solution reaching every aspiration level"
    )
    assert d_phi_indicator(np.array([[0.1, 0.21]]), aspiration, reservation).ci < 0, (
        "CI is non-negative for a solution missing an aspiration level"
    )


@pytest.mark.indicators
def test_d_phi_monotonicity():
    """Test that D-PHI rewards better and more numerous solutions."""
    aspiration = np.array([0.2, 0.2])
    reservation = np.array([0.6, 0.6])
    solutions = np.array([[0.3, 0.5], [0.5, 0.3]])

    base = d_phi_indicator(solutions, aspiration, reservation)
    dominating = d_phi_indicator(solutions - 0.05, aspiration, reservation)
    extended = d_phi_indicator(np.vstack((solutions, [[0.4, 0.4]])), aspiration, reservation)
    with_dominated = d_phi_indicator(np.vstack((solutions, [[0.9, 0.9]])), aspiration, reservation)

    assert dominating.d_phi > base.d_phi, "A dominating set does not have a larger D-PHI"
    assert dominating.ci > base.ci, "A dominating set does not have a larger CI"
    assert extended.d_phi > base.d_phi, "Adding a non-dominated solution does not increase D-PHI"
    assert np.isclose(with_dominated.d_phi, base.d_phi), "Adding a dominated solution changed D-PHI"


@pytest.mark.indicators
def test_d_phi_batch():
    """Test the batch version of D-PHI."""
    aspiration = np.array([0.2, 0.2])
    reservation = np.array([0.6, 0.6])
    solution_sets = {"good": np.array([[0.25, 0.3], [0.3, 0.25]]), "bad": np.array([[0.7, 0.8], [0.8, 0.7]])}

    results = d_phi_batch(solution_sets, aspiration, reservation)

    assert set(results.keys()) == set(solution_sets.keys()), "The batch version lost a solution set"
    assert results["good"].d_phi > results["bad"].d_phi, "The better set does not have a larger D-PHI"
    assert results["good"].ci > results["bad"].ci, "The better set does not have a larger CI"
    for set_name, sols in solution_sets.items():
        assert np.isclose(results[set_name].d_phi, d_phi_indicator(sols, aspiration, reservation).d_phi), (
            f"The batch version disagrees with the single set version for {set_name}"
        )


@pytest.mark.indicators
def test_d_phi_invalid_preferences():
    """Test that D-PHI rejects inconsistent preference information."""
    solutions = np.array([[0.3, 0.3]])

    with pytest.raises(ValueError, match="one value per objective"):
        d_phi_indicator(solutions, np.array([0.1, 0.2, 0.3]), np.array([0.5, 0.6, 0.7]))
    with pytest.raises(ValueError, match="aspiration level"):
        d_phi_indicator(solutions, np.array([0.7, 0.2]), np.array([0.5, 0.6]))
    with pytest.raises(ValueError, match="'c1'"):
        d_phi_indicator(solutions, np.array([0.1, 0.2]), np.array([0.5, 0.6]), c1=0.0, c2=1.0)
    with pytest.raises(ValueError, match="positive"):
        d_phi_indicator(solutions, np.array([0.1, 0.2]), np.array([0.5, 0.6]), epsilon_a=0.0)


@pytest.mark.indicators
def test_phi_plus_indicator():
    """Test PHI+ on solution sets with known indicator values."""
    reference_point = np.array([0.5, 0.5])
    deviations = np.array([0.1, 0.1])

    # The region of interest is [0.4, 0.6]^2. A single solution at the reference point covers 0.1 * 0.1 of it,
    # and the largest coverage attainable without dominating the reference point is 0.2 * 0.2 - 0.1 * 0.1.
    at_rp = phi_plus_indicator(reference_point[np.newaxis, :], reference_point, deviations, deviations)
    assert np.isclose(at_rp.phi_plus, 0.01 / 0.03), "PHI+ is not correct at the reference point"

    # A solution at the lower point dominates the reference point, so the coverage is measured against the
    # hypervolume of the reference point instead, and the indicator exceeds one.
    at_lower = phi_plus_indicator(
        (reference_point - deviations)[np.newaxis, :], reference_point, deviations, deviations
    )
    assert np.isclose(at_lower.phi_plus, 0.04 / 0.01), "PHI+ is not correct for a solution dominating the rp"

    # Solutions outside the region of interest do not contribute.
    outside = np.array([[0.9, 0.1], [0.1, 0.9]])
    assert phi_plus_indicator(outside, reference_point, deviations, deviations).phi_plus == 0.0, (
        "PHI+ is not 0 when the region of interest is empty"
    )
    assert np.isclose(
        phi_plus_indicator(np.vstack((reference_point, outside)), reference_point, deviations, deviations).phi_plus,
        at_rp.phi_plus,
    ), "Solutions outside the region of interest changed PHI+"

    assert phi_plus_indicator(np.empty((0, 2)), reference_point, deviations, deviations).phi_plus == 0.0, (
        "PHI+ is not 0 for an empty solution set"
    )


@pytest.mark.indicators
def test_phi_plus_invalid_deviations():
    """Test that PHI+ rejects deviations that do not define a usable region of interest."""
    solutions = np.array([[0.5, 0.5]])
    reference_point = np.array([0.5, 0.5])

    with pytest.raises(ValueError, match="'deviations_lower'"):
        phi_plus_indicator(solutions, reference_point, -0.1, 0.1)
    with pytest.raises(ValueError, match="'deviations_upper'"):
        phi_plus_indicator(solutions, reference_point, 0.1, 0.0)
    with pytest.raises(ValueError, match="one value per objective"):
        phi_plus_indicator(solutions, reference_point, np.array([0.1, 0.1, 0.1]), 0.1)

    # A zero lower deviation is fine: the region of interest simply is not extended past the reference point.
    assert phi_plus_indicator(np.array([[0.52, 0.55]]), reference_point, 0.0, 0.1).phi_plus > 0, (
        "A zero lower deviation is not accepted"
    )


@pytest.mark.indicators
def test_phi_plus_monotonicity():
    """Test that PHI+ rewards a better coverage of the region of interest."""
    reference_point = np.array([0.5, 0.5])
    deviations = np.array([0.1, 0.1])
    sparse = np.array([[0.45, 0.58], [0.58, 0.45]])
    dense = np.vstack((sparse, [[0.5, 0.5], [0.48, 0.54], [0.54, 0.48]]))

    sparse_value = phi_plus_indicator(sparse, reference_point, deviations, deviations).phi_plus
    dense_value = phi_plus_indicator(dense, reference_point, deviations, deviations).phi_plus

    assert 0 < sparse_value < dense_value, "A denser set in the region of interest does not have a larger PHI+"


@pytest.mark.indicators
def test_phi_plus_batch():
    """Test the batch version of PHI+."""
    reference_point = np.array([0.5, 0.5])
    deviations = np.array([0.15, 0.15])
    solution_sets = {
        "in_roi": np.array([[0.45, 0.5], [0.5, 0.45]]),
        "outside_roi": np.array([[0.95, 0.05], [0.05, 0.95]]),
    }

    results = phi_plus_batch(solution_sets, reference_point, deviations, deviations)

    assert set(results.keys()) == set(solution_sets.keys()), "The batch version lost a solution set"
    assert results["in_roi"].phi_plus > 0, "PHI+ is 0 for a set covering the region of interest"
    assert results["outside_roi"].phi_plus == 0.0, "PHI+ is not 0 for a set outside the region of interest"
    for set_name, sols in solution_sets.items():
        assert np.isclose(
            results[set_name].phi_plus,
            phi_plus_indicator(sols, reference_point, deviations, deviations).phi_plus,
        ), f"The batch version disagrees with the single set version for {set_name}"
