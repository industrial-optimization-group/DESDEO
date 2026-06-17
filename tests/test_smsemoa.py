"""Tests for the SMS-EMOA algorithm and its hypervolume-based selection operator."""

import moocore
import numpy as np
import pytest

from desdeo.emo.operators.selection import (
    SMSEMOASelector,
    _count_dominating_points,
    _hv_contributions_2d,
)
from desdeo.emo.options.algorithms import smsemoa_options
from desdeo.emo.options.templates import emo_constructor
from desdeo.problem.testproblems import dtlz2, re22, zdt1, zdt2
from desdeo.tools.non_dominated_sorting import non_dominated
from desdeo.tools.patterns import Publisher


def _make_selector(problem, population_size, use_dominating_points=True, greedy_reduction=True):
    """Build an SMS-EMOA selector for unit testing (verbosity 0 to avoid needing other components)."""
    return SMSEMOASelector(
        problem=problem,
        verbosity=0,
        publisher=Publisher(),
        population_size=population_size,
        use_dominating_points=use_dominating_points,
        greedy_reduction=greedy_reduction,
    )


def test_hv_contributions_2d_known_values():
    """The 2D contribution formula matches the exact values and keeps the two boundary points."""
    # A non-dominated bi-objective front (minimization).
    front = np.array([[0.0, 3.0], [1.0, 2.0], [2.0, 1.0], [3.0, 0.0]])
    contrib = _hv_contributions_2d(front)
    # Boundary points have infinite contribution and are therefore never removed.
    assert np.isinf(contrib[0])
    assert np.isinf(contrib[3])
    # Interior contributions: (f1_next - f1_i) * (f2_prev - f2_i).
    assert contrib[1] == pytest.approx((2.0 - 1.0) * (3.0 - 2.0))
    assert contrib[2] == pytest.approx((3.0 - 2.0) * (2.0 - 1.0))


def test_hv_contributions_2d_small_front():
    """Fronts with two or fewer points are all boundary points (kept)."""
    assert np.all(np.isinf(_hv_contributions_2d(np.array([[0.0, 1.0], [1.0, 0.0]]))))
    assert np.all(np.isinf(_hv_contributions_2d(np.array([[0.0, 1.0]]))))


def test_hv_contributions_2d_least_in_middle():
    """A point in a dense region contributes the least and is the removal candidate."""
    # Two points are clustered close together around f1 ~1.0; one of them should contribute the least.
    front = np.array([[0.0, 3.0], [0.9, 1.1], [1.0, 1.0], [3.0, 0.0]])
    contrib = _hv_contributions_2d(front)
    assert int(np.argmin(contrib)) in (1, 2)


def test_count_dominating_points():
    """The dominating-points count matches manual counting."""
    # Point 0 dominates 1, 2, 3. Point 1 dominates 3. Points are in minimization form.
    fitness = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.5], [3.0, 3.0]])
    candidates = np.array([1, 2, 3])
    counts = _count_dominating_points(fitness, candidates)
    # 1 is dominated by {0}; 2 is dominated by {0}; 3 is dominated by {0, 1, 2}.
    assert counts.tolist() == [1, 1, 3]


def test_reduce_keeps_population_size_and_boundaries():
    """The reduce step returns exactly ``population_size`` survivors and keeps 2D boundary solutions."""
    problem = zdt1(number_of_variables=10)
    selector = _make_selector(problem, population_size=4)
    # 6 mutually non-dominated points; the two extremes must always survive.
    targets = np.array([[0.0, 5.0], [1.0, 4.0], [2.0, 3.0], [3.0, 2.0], [4.0, 1.0], [5.0, 0.0]])
    survivors = selector._reduce(targets, num_remove=2)
    assert len(survivors) == 4
    assert 0 in survivors  # extreme (best f1)
    assert 5 in survivors  # extreme (best f2)


def test_reduce_hypervolume_non_decreasing():
    """Reducing a population never decreases its dominated hypervolume (the SMS-EMOA invariant)."""
    problem = zdt1(number_of_variables=10)
    selector = _make_selector(problem, population_size=9, use_dominating_points=False)
    # A dense, mutually non-dominated front on a concave (quarter-circle) curve.
    theta = np.linspace(0.0, np.pi / 2, 12)
    targets = np.column_stack([1 - np.cos(theta), 1 - np.sin(theta)])
    ref = np.array([1.1, 1.1])
    hv_before = moocore.hypervolume(targets, ref=ref)
    survivors = selector._reduce(targets, num_remove=3)
    hv_after = moocore.hypervolume(targets[survivors], ref=ref)
    assert len(survivors) == 9
    # Removing the least-contributing points keeps the hypervolume as high as possible: it can only
    # shrink slightly (we removed interior points from a dense front, keeping the boundaries).
    assert hv_after <= hv_before + 1e-12
    assert hv_after > 0.97 * hv_before
    # Both extremes of the front survive.
    assert 0 in survivors
    assert 11 in survivors


def test_batch_reduce_keeps_size_and_boundaries():
    """The batched reduction returns exactly ``population_size`` survivors and keeps 2D boundary solutions."""
    problem = zdt1(number_of_variables=10)
    selector = _make_selector(problem, population_size=6, greedy_reduction=False)
    # A dense, mutually non-dominated front; the two extremes (infinite contribution) must survive.
    theta = np.linspace(0.0, np.pi / 2, 12)
    targets = np.column_stack([1 - np.cos(theta), 1 - np.sin(theta)])
    survivors = selector._reduce(targets, num_remove=6)
    assert len(survivors) == 6
    assert 0 in survivors
    assert 11 in survivors


def test_batch_reduce_preserves_most_hypervolume():
    """Batched removal keeps most of the dominated hypervolume (cheaper approximation of the greedy rule)."""
    problem = dtlz2(n_variables=7, n_objectives=3)
    selector = _make_selector(problem, population_size=20, use_dominating_points=False, greedy_reduction=False)
    rng = np.random.default_rng(0)
    # A non-dominated cloud on the positive octant of a sphere (3 objectives, minimization).
    pts = np.abs(rng.normal(size=(40, 3)))
    pts /= np.linalg.norm(pts, axis=1, keepdims=True)
    pts = pts[non_dominated(pts)]
    ref = np.full(3, 1.1)
    hv_before = moocore.hypervolume(pts, ref=ref)
    keep = max(1, len(pts) - 5)
    survivors = selector._reduce(pts, num_remove=len(pts) - keep)
    assert len(survivors) == keep
    hv_after = moocore.hypervolume(pts[survivors], ref=ref)
    assert hv_after > 0.9 * hv_before


def test_reduce_removes_dominated_first():
    """When a clearly dominated solution is present, it is discarded before non-dominated ones."""
    problem = zdt1(number_of_variables=10)
    selector = _make_selector(problem, population_size=3, use_dominating_points=True)
    targets = np.array([[0.0, 2.0], [1.0, 1.0], [2.0, 0.0], [3.0, 3.0]])  # last point is dominated by all
    survivors = selector._reduce(targets, num_remove=1)
    assert 3 not in survivors
    assert sorted(survivors.tolist()) == [0, 1, 2]


@pytest.mark.ea
def test_smsemoa_zdt1():
    """SMS-EMOA converges to and spreads along the ZDT1 Pareto front."""
    problem = zdt1(number_of_variables=30)
    opts = smsemoa_options(population_size=100, n_offspring=20, max_evaluations=15000, seed=1)
    solver, _ = emo_constructor(opts, problem)
    res = solver()
    out = res.optimal_outputs
    assert len(out) == 100
    # ZDT1 Pareto front: f2 = 1 - sqrt(f1), f1 in [0, 1]. Convergence => f2 close to the front.
    f1 = out["f_1"].to_numpy()
    f2 = out["f_2"].to_numpy()
    front_f2 = 1 - np.sqrt(np.clip(f1, 0, 1))
    assert np.median(f2 - front_f2) < 0.02  # close to the true front
    assert f1.max() - f1.min() > 0.8  # well spread along the front


@pytest.mark.ea
def test_smsemoa_zdt2_basic_variant():
    """The basic (pure hypervolume) variant also converges on the concave ZDT2 front."""
    problem = zdt2(n_variables=30)
    opts = smsemoa_options(
        population_size=100, n_offspring=20, max_evaluations=15000, use_dominating_points=False, seed=1
    )
    solver, _ = emo_constructor(opts, problem)
    res = solver()
    out = res.optimal_outputs
    f1 = out["f_1"].to_numpy()
    f2 = out["f_2"].to_numpy()
    front_f2 = 1 - np.clip(f1, 0, 1) ** 2
    assert np.median(f2 - front_f2) < 0.02
    assert f1.max() - f1.min() > 0.8


@pytest.mark.ea
def test_smsemoa_dtlz2():
    """SMS-EMOA places solutions on the DTLZ2 unit-sphere Pareto front (three objectives)."""
    problem = dtlz2(n_variables=12, n_objectives=3)
    opts = smsemoa_options(population_size=100, n_offspring=20, max_evaluations=20000, seed=1)
    solver, _ = emo_constructor(opts, problem)
    res = solver()
    out = res.optimal_outputs
    norm = (out["f_1"] ** 2 + out["f_2"] ** 2 + out["f_3"] ** 2).sqrt()
    # Most solutions should lie on the unit sphere (norm ~1).
    assert norm.median() < 1.05


@pytest.mark.ea
def test_smsemoa_batch_reduction_end_to_end():
    """The fast batched-reduction variant still converges to the DTLZ2 unit-sphere front."""
    problem = dtlz2(n_variables=12, n_objectives=3)
    opts = smsemoa_options(population_size=100, n_offspring=100, max_evaluations=15000, greedy_reduction=False, seed=1)
    solver, _ = emo_constructor(opts, problem)
    res = solver()
    out = res.optimal_outputs
    norm = (out["f_1"] ** 2 + out["f_2"] ** 2 + out["f_3"] ** 2).sqrt()
    assert norm.median() < 1.1


@pytest.mark.ea
def test_smsemoa_constraints_not_supported():
    """The selector clearly rejects constrained problems (not yet supported)."""
    with pytest.raises(NotImplementedError):
        _make_selector(re22(), population_size=10)
