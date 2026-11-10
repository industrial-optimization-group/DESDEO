"""Tests for the SingleObjectiveConstrainedRankingSelector."""

import numpy as np
import polars as pl
import pytest

from desdeo.emo import algorithms, generator, selection, termination
from desdeo.emo.operators.selection import SingleObjectiveConstrainedRankingSelector
from desdeo.emo.options.scalar_selection import TournamentSelectionOptions, scalar_selector_constructor
from desdeo.problem.testproblems.single_objective import new_branin_function
from desdeo.tools.patterns import Publisher


def _selector(mode: str, constraints: dict[str, float], population_size: int, **kwargs):
    return SingleObjectiveConstrainedRankingSelector(
        problem=new_branin_function(),
        verbosity=0,
        publisher=Publisher(),
        population_size=population_size,
        target_objective_symbol="f_1",
        mode=mode,
        constraints=constraints,
        **kwargs,
    )


# A small pool with one constraint and threshold 1.0: indices 0 and 1 are strictly feasible, 2 and 4 lie
# in the relaxed band, 3 lies beyond the threshold.
F = np.array([3.0, 1.0, 2.0, 0.0, 5.0])
C = np.array([[-1.0], [-0.5], [0.5], [2.0], [0.2]])


@pytest.mark.ea
def test_baseline_order():
    """Feasible solutions by objective first, then infeasible ones by their normalized violation."""
    order = _selector("baseline", {"c_1": 1.0}, 5).compute_order(F, C)
    np.testing.assert_array_equal(order, [1, 0, 4, 2, 3])


@pytest.mark.ea
def test_relaxed_round_robin():
    """Picks alternate between the strict ranking and the ranking with the constraint relaxed."""
    order = _selector("relaxed", {"c_1": 1.0}, 5).compute_order(F, C)
    # Strict ranking: 1, 0, 4, 2, 3. Relaxed ranking: 1, 2, 0, 4, 3. Round robin, skipping chosen ones.
    np.testing.assert_array_equal(order, [1, 2, 0, 4, 3])


@pytest.mark.ea
def test_relaxed_zero_threshold_gets_no_pool():
    """A constraint with threshold 0 is not relaxed and adds no pool (which would duplicate the strict one).

    Indices 0-2 are strictly feasible (f = 0, 1, 2); 3 and 4 violate c_1 by 0.5 and 0.8 and have the best
    objectives. Strict ranking: 0, 1, 2, 3, 4. Ranking with c_1 relaxed to 1: 4, 3, 0, 1, 2. With the pools
    (strict, c_1) the round robin gives 0, 4, 1, 3, 2; a duplicate strict pool for c_2 would give
    0, 4, 1, 2, 3.
    """
    f = np.array([0.0, 1.0, 2.0, -1.0, -2.0])
    c = np.array([[-1.0, -1.0], [-1.0, -1.0], [-1.0, -1.0], [0.5, -1.0], [0.8, -1.0]])
    order = _selector("relaxed", {"c_1": 1.0, "c_2": 0.0}, 5).compute_order(f, c)
    np.testing.assert_array_equal(order, [0, 4, 1, 3, 2])


@pytest.mark.ea
@pytest.mark.parametrize("mode", ["relaxed", "ranking"])
def test_zero_threshold_constraint_adds_no_ranking(mode):
    """A constraint with a zero threshold gets no ranking of its own: the mode builds the strict ranking
    and one ranking per constraint with a positive threshold."""
    rng = np.random.default_rng(3)
    f = rng.normal(size=30)
    c = rng.normal(size=(30, 3)) * 0.5
    sel = _selector(mode, {"c_1": 0.4, "c_2": 0.0, "c_3": 0.3}, 12)
    built = []
    original = sel._order_by_objective_then_violation

    def counting(target, v):
        built.append(1)
        return original(target, v)

    sel._order_by_objective_then_violation = counting
    order = sel.compute_order(f, c)
    assert len(set(order.tolist())) == 12
    assert len(built) == 3  # strict, c_1, c_3


@pytest.mark.ea
@pytest.mark.parametrize("mode", ["relaxed", "ranking"])
def test_all_zero_thresholds_behave_like_baseline(mode):
    """If no constraint is relaxed, the relaxed and ranking modes keep only the strict ranking."""
    rng = np.random.default_rng(5)
    f = rng.normal(size=20)
    c = rng.normal(size=(20, 2))
    order = _selector(mode, {"c_1": 0.0, "c_2": 0.0}, 10).compute_order(f, c)
    baseline = _selector("baseline", {"c_1": 0.0, "c_2": 0.0}, 10).compute_order(f, c)
    np.testing.assert_array_equal(order, baseline)


@pytest.mark.ea
def test_joint_round_robin():
    """Picks alternate between the strict ranking and the ranking with all constraints relaxed at once.

    Index 0 is strictly feasible, 2 needs only c_1 relaxed, 1 needs both relaxed, and 3 lies beyond the
    threshold of c_1. Strict ranking: 0, 2, 3, 1. Joint ranking: 1, 2, 0, 3.
    """
    f = np.array([3.0, 0.0, 1.0, -1.0])
    c = np.array([[-1.0, -1.0], [0.5, 0.5], [0.5, -1.0], [2.0, -1.0]])
    constraints = {"c_1": 1.0, "c_2": 1.0}
    order = _selector("joint", constraints, 4).compute_order(f, c)
    np.testing.assert_array_equal(order, [0, 1, 2, 3])
    # The relaxed mode relaxes one constraint at a time, so it does not favour index 1.
    assert _selector("relaxed", constraints, 4).compute_order(f, c)[:2].tolist() == [0, 2]


@pytest.mark.ea
def test_joint_equals_relaxed_with_one_constraint():
    """With a single constraint, the joint and relaxed modes give the same order."""
    np.testing.assert_array_equal(
        _selector("joint", {"c_1": 1.0}, 5).compute_order(F, C),
        _selector("relaxed", {"c_1": 1.0}, 5).compute_order(F, C),
    )


@pytest.mark.ea
@pytest.mark.parametrize("niching", ["crowding", "knearest", "kth"])
def test_ranking_returns_distinct_indices(niching):
    """The ranking mode returns population_size distinct indices, deterministically."""
    rng = np.random.default_rng(1)
    f = rng.normal(size=40)
    c = rng.uniform(-1.0, 2.0, size=(40, 3))
    constraints = {"c_1": 0.5, "c_2": 1.0, "c_3": 0.8}
    first = _selector("ranking", constraints, 20, niching=niching).compute_order(f, c)
    second = _selector("ranking", constraints, 20, niching=niching).compute_order(f, c)
    assert len(first) == 20
    assert len(set(first.tolist())) == 20
    np.testing.assert_array_equal(first, second)


@pytest.mark.ea
def test_hypervolume_single_box_member_first():
    """With a single threshold-feasible solution, it is ranked first and the rest follow by violation."""
    f = np.array([0.0, 2.0, 1.0])
    c = np.array([[3.0], [0.5], [4.0]])
    order = _selector("hypervolume", {"c_1": 1.0}, 3).compute_order(f, c)
    np.testing.assert_array_equal(order, [1, 0, 2])


@pytest.mark.ea
def test_hypervolume_keeps_box_optimum_first():
    """The best threshold-feasible solution (a protected end point) is ranked first."""
    order = _selector("hypervolume", {"c_1": 1.0}, 5).compute_order(F, C)
    assert order[0] == 1
    assert sorted(order.tolist()) == [0, 1, 2, 3, 4]


@pytest.mark.ea
def test_hypervolume_orders_dominated_solutions_by_front():
    """Dominated solutions are ordered by their non-dominated front, not by their objective.

    Shadow-front points (objective, relaxation used): a (0, 1), m (5, 0.5) and s (10, 0) form the
    first front; z (1, 1) and x (6, 0.6) are dominated once and form the second; y (3, 1) is also
    dominated by z and forms the third. So x is ranked before y although y has the better objective.
    """
    f = np.array([0.0, 5.0, 10.0, 6.0, 1.0, 3.0])
    c = np.array([[1.0], [0.5], [-1.0], [0.6], [1.0], [1.0]])
    order = _selector("hypervolume", {"c_1": 1.0}, 6).compute_order(f, c)
    assert set(order[:3].tolist()) == {0, 1, 2}
    assert set(order[3:5].tolist()) == {3, 4}
    assert order[5] == 5


@pytest.mark.ea
def test_hypervolume_protects_end_points_with_tied_objectives():
    """With ties in the objective, the protected end points are taken from the first front.

    Solutions 0 and 1 share the best objective, but 0 uses more relaxation, so it is dominated by 1
    and not on the first front. Taking the first minimizer over the whole box (0) as the protected
    end point used to fail; the end point is 1. The strictly feasible 3 and 4 tie as duplicates.
    """
    f = np.array([0.0, 0.0, 5.0, 10.0, 10.0, 11.0])
    c = np.array([[0.8], [0.2], [0.1], [-1.0], [-0.5], [-1.0]])
    order = _selector("hypervolume", {"c_1": 1.0}, 6).compute_order(f, c)
    assert sorted(order.tolist()) == [0, 1, 2, 3, 4, 5]
    assert order[0] == 1
    assert order.tolist().index(0) > order.tolist().index(1)


@pytest.mark.ea
def test_hypervolume_stops_at_population_size():
    """With a smaller population, the first front is kept whole and filled up from the second."""
    f = np.array([0.0, 5.0, 10.0, 6.0, 1.0, 3.0])
    c = np.array([[1.0], [0.5], [-1.0], [0.6], [1.0], [1.0]])
    order = _selector("hypervolume", {"c_1": 1.0}, 4).compute_order(f, c)
    assert len(order) == 4
    assert set(order[:3].tolist()) == {0, 1, 2}
    assert order[3] in {3, 4}


@pytest.mark.ea
def test_unknown_mode_raises():
    """An unknown mode is rejected."""
    with pytest.raises(ValueError, match="Unsupported mode"):
        _selector("unknown", {"c_1": 1.0}, 5).compute_order(F, C)


def _pool(x: np.ndarray, f: np.ndarray, c: np.ndarray) -> tuple[pl.DataFrame, pl.DataFrame]:
    sols = pl.DataFrame({"x_1": x[:, 0], "x_2": x[:, 1]})
    outs = pl.DataFrame({"f_1_min": f, **{f"c_{j + 1}": c[:, j] for j in range(c.shape[1])}})
    return sols, outs


@pytest.mark.ea
@pytest.mark.parametrize("mode", ["baseline", "relaxed", "ranking", "hypervolume", "joint"])
def test_do_removes_decision_space_duplicates(mode):
    """Solutions with identical decision vectors are kept only once."""
    x = np.array([[0.1, 0.2], [0.3, 0.4], [0.1, 0.2], [0.5, 0.6], [0.3, 0.4], [0.7, 0.8]])
    f = np.array([1.0, 2.0, 1.0, 3.0, 2.0, 0.5])
    c = np.array([[-1.0], [0.5], [-1.0], [0.2], [0.5], [3.0]])
    sols, outs = _pool(x, f, c)
    new_sols, new_outs = _selector(mode, {"c_1": 1.0}, 6).do((sols[:3], outs[:3]), (sols[3:], outs[3:]))
    assert new_sols.height == 4
    assert new_sols.unique().height == 4
    assert new_outs.height == 4


@pytest.mark.ea
@pytest.mark.parametrize("mode", ["baseline", "relaxed", "ranking", "hypervolume", "joint"])
def test_published_fitness_is_higher_is_better(mode):
    """The fitness read by the mating tournament decreases from the best-ranked solution, and is positive."""
    rng = np.random.default_rng(2)
    x = rng.uniform(size=(30, 2))
    f = rng.normal(size=30)
    c = rng.uniform(-1.0, 2.0, size=(30, 2))
    sols, outs = _pool(x, f, c)
    sel = _selector(mode, {"c_1": 0.5, "c_2": 1.0}, 15)
    new_sols, _ = sel.do((sols[:15], outs[:15]), (sols[15:], outs[15:]))
    np.testing.assert_array_equal(sel.fitness, np.arange(new_sols.height, 0, -1))


@pytest.mark.ea
def test_tournament_prefers_better_ranks():
    """A binary tournament on the published fitness picks better-ranked parents more often than chance."""
    rng = np.random.default_rng(3)
    n = 12
    x = rng.uniform(size=(2 * n, 2))
    f = rng.normal(size=2 * n)
    c = rng.uniform(-1.0, 2.0, size=(2 * n, 1))
    sols, outs = _pool(x, f, c)
    sel = _selector("relaxed", {"c_1": 1.0}, n)
    new_sols, new_outs = sel.do((sols[:n], outs[:n]), (sols[n:], outs[n:]))
    position = {v: i for i, v in enumerate(new_sols["x_1"].to_list())}

    tournament = scalar_selector_constructor(
        TournamentSelectionOptions(tournament_size=2, winner_size=n), seed=4, publisher=Publisher(), verbosity=0
    )
    ranks = []
    for _ in range(500):
        winners, _ = tournament.do((new_sols, new_outs), fitness=sel.fitness)
        ranks.extend(position[v] for v in winners["x_1"].to_list())
    # Random choice gives a mean rank of (n - 1) / 2 = 5.5, the better of two members about 3.5.
    assert np.mean(ranks) < 4.0


def _nsga2_run(seed: int):
    problem = new_branin_function()
    options = algorithms.nsga2_options()
    options.template.seed = seed
    options.template.selection = selection.SingleObjectiveConstrainedRankingSelectorOptions(
        population_size=12,
        target_objective_symbol="f_1",
        constraints={"c_1": 15.0},
        mode="relaxed",
        niching="kth",
    )
    options.template.mate_selection = TournamentSelectionOptions(tournament_size=2, winner_size=12)
    options.template.generator = generator.LHSGeneratorOptions(n_points=12)
    options.template.termination = termination.MaxGenerationsTerminatorOptions(max_generations=15)
    solver, _ = algorithms.emo_constructor(emo_options=options, problem=problem)
    return solver()


@pytest.mark.ea
def test_nsga2_with_selector_is_reproducible():
    """The selector works inside NSGA-II (Template2), and equal seeds give equal runs."""
    first = _nsga2_run(seed=5)
    second = _nsga2_run(seed=5)
    assert first.optimal_variables.height == 12
    assert first.optimal_variables.equals(second.optimal_variables)
    assert first.optimal_outputs.equals(second.optimal_outputs)
