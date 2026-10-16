"""Tests for Evolutionary Algorithms."""

from contextlib import suppress

import numpy as np
import polars as pl
import pytest

from desdeo.emo import algorithms
from desdeo.emo.operators.selection import ParameterAdaptationStrategy, RVEASelector
from desdeo.emo.options.generator import ArchiveGeneratorOptions
from desdeo.emo.options.termination import (
    CompositeTerminatorOptions,
    MaxEvaluationsTerminatorOptions,
    MaxGenerationsTerminatorOptions,
)
from desdeo.problem.evaluator import PolarsEvaluator
from desdeo.problem.testproblems import (
    car_side_impact,
    dtlz2,
    momip_ti2,
    river_pollution_problem,
)


@pytest.mark.ea
def test_nsga2_dtlz2():
    """Test whether the 'default' NSGA-II variant can be initialized and run as a whole."""
    n_vars = 12
    n_objs = 3
    problem = dtlz2(n_vars, n_objs)

    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.nsga2_options())

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front
    median = norm.median()
    assert isinstance(median, float)
    assert median < 1.1


@pytest.mark.ea
def test_nsga3_dtlz2():
    """Test whether the NSGA-III algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.nsga3_options())

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front
    median = norm.median()
    assert isinstance(median, float)
    assert median < 1.1


@pytest.mark.ea
def test_rvea_dtlz2():
    """Test whether the RVEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.rvea_options())

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front
    median = norm.median()
    assert isinstance(median, float)
    assert median < 1.1


@pytest.mark.ea
def test_ibea_dtlz2():
    """Test whether the IBEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.ibea_options())

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front
    median = norm.median()
    assert isinstance(median, float)
    assert median < 1.1


@pytest.mark.ea
def test_smsemoa_dtlz2():
    """Test whether the SMS-EMOA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    options = algorithms.sms_emoa_options()
    solver, _extras = algorithms.emo_constructor(emo_options=options, problem=problem)
    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front

    assert norm.median() < 1.3  # Really bad convergence to save time.


@pytest.mark.ea
def test_mixed_integer_nsga3():
    """Test whether the mixed-integer NSGA-III variant can be initialized and run as a whole."""
    problem = momip_ti2()
    with suppress(NotImplementedError):
        solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.nsga3_mixed_integer_options())
        _ = solver()


@pytest.mark.ea
def test_nsga3_river():
    """Test whether the 'default' NSGA-III variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.nsga3_options())

    _ = solver()


@pytest.mark.ea
def test_mixed_integer_rvea():
    """Test whether the mixed-integer RVEA variant can be initialized and run as a whole."""
    problem = momip_ti2()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.rvea_mixed_integer_options())

    _ = solver()


@pytest.mark.ea
def test_mixed_integer_smsemoa():
    """Test whether the mixed-integer SMS-EMOA variant can be initialized and run as a whole."""
    problem = momip_ti2()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.sms_emoa_mixed_integer_options())
    _ = solver()


@pytest.mark.ea
def test_rvea_river():
    """Test whether the 'default' RVEA variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.rvea_options())

    _ = solver()


@pytest.mark.ea
def test_mixed_integer_ibea():
    """Test whether the mixed-integer IBEA variant can be initialized and run as a whole."""
    problem = momip_ti2()
    with suppress(NotImplementedError):
        solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.ibea_mixed_integer_options())
        _ = solver()


@pytest.mark.ea
def test_ibea_river():
    """Test whether the 'default' IBEA variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=algorithms.ibea_options())

    _ = solver()


@pytest.mark.ea
def test_rvea_survives_a_generation_with_no_feasible_member():
    """RVEA tracks its ideal over feasible members; a generation may have none.

    On a tightly constrained problem the initial population can be entirely
    infeasible, and a contracted population can lose its last feasible member
    later. The ideal update used to take a minimum over an empty selection and
    raise; it now keeps the previous ideal, or takes it over every member when
    there is none yet, as the nadir update already did.
    """
    problem = car_side_impact(three_obj=True)
    symbols = [variable.symbol for variable in problem.variables]
    lows = np.array([variable.lowerbound for variable in problem.variables], dtype=float)
    spans = np.array([variable.upperbound - variable.lowerbound for variable in problem.variables], dtype=float)

    rng = np.random.default_rng(0)
    starts = lows + 0.02 * spans * rng.random((24, len(symbols)))
    frame = pl.DataFrame(starts, schema=symbols, orient="row")

    options = algorithms.rvea_options()
    options.template.generator = ArchiveGeneratorOptions(solutions=frame, outputs=pl.DataFrame())
    options.template.termination.max_generations = 4
    options.template.selection.reference_vector_options.number_of_vectors = 24
    options.template.selection.reference_vector_options.lattice_resolution = None

    solver, extras = algorithms.emo_constructor(problem=problem, emo_options=options)
    _ = solver()

    assert extras.archive is not None and extras.archive.selections is not None
    assert len(extras.archive.selections) > 0


@pytest.mark.ea
def test_rvea_replaces_a_provisional_ideal_once_a_feasible_member_appears():
    """An ideal taken over infeasible members must not outlive them.

    Infeasible designs can score far better than any feasible one, so an ideal
    minimised into from them would stay wrong for the rest of the run. The
    first feasible member replaces the provisional ideal outright; after that
    the ideal is minimised into as usual.
    """
    problem = car_side_impact(three_obj=True)
    symbols = [variable.symbol for variable in problem.variables]
    lows = np.array([variable.lowerbound for variable in problem.variables], dtype=float)
    spans = np.array([variable.upperbound - variable.lowerbound for variable in problem.variables], dtype=float)
    constraints = [c.symbol for c in problem.constraints]
    targets = [f"{o.symbol}_min" for o in problem.objectives]

    options = algorithms.rvea_options()
    options.template.selection.reference_vector_options.number_of_vectors = 24
    options.template.selection.reference_vector_options.lattice_resolution = None
    _, extras = algorithms.emo_constructor(problem=problem, emo_options=options)
    selectors = {s for members in extras.publisher.subscribers.values() for s in members if isinstance(s, RVEASelector)}
    assert len(selectors) == 1
    selector = selectors.pop()
    # The penalty schedule is normally fed by the terminator's messages.
    selector.numerator, selector.denominator = 1, 100
    evaluator = PolarsEvaluator(problem)

    def evaluated(designs: np.ndarray) -> tuple[pl.DataFrame, pl.DataFrame]:
        frame = pl.DataFrame(designs, schema=symbols, orient="row")
        outputs = evaluator.evaluate(frame)
        return frame, outputs.select([c for c in outputs.columns if c not in symbols])

    rng = np.random.default_rng(0)
    # Thin panels everywhere: every design breaks a constraint, and scores well for it.
    corner = evaluated(lows + 0.02 * spans * rng.random((12, len(symbols))))
    assert not (corner[1][constraints].to_numpy() <= 0).all(axis=1).any()
    selector.do(corner, corner)
    assert selector._ideal_is_provisional
    provisional = selector.ideal.copy()

    # Now a population with feasible members, found by drawing until enough exist.
    draws = evaluated(lows + spans * rng.random((400, len(symbols))))
    feasible = (draws[1][constraints].to_numpy() <= 0).all(axis=1)
    assert feasible.sum() >= 12
    keep = np.flatnonzero(feasible)[:12]
    mixed = (draws[0][keep], draws[1][keep])
    selector.do(mixed, corner)
    assert not selector._ideal_is_provisional
    feasible_ideal = mixed[1][targets].to_numpy().min(axis=0)
    # Replaced outright: the ideal is the feasible members' own, not the corner's better one.
    np.testing.assert_allclose(selector.ideal, feasible_ideal)
    assert np.any(provisional < feasible_ideal)

    # From here on, minimised into as usual.
    better = evaluated(draws[0][np.flatnonzero(feasible)[12:24]].to_numpy())
    selector.do(better, better)
    expected = np.minimum(feasible_ideal, better[1][targets].to_numpy().min(axis=0))
    np.testing.assert_allclose(selector.ideal, expected)


@pytest.mark.ea
def test_an_evaluation_limit_inside_a_composite_terminator_binds():
    """The template subscribes only top-level components, so a composite must forward.

    Before, an evaluation limit wrapped in a composite never counted and the
    run went to the generation cap; the generation limit still bound because it
    counts in its own check.
    """
    problem = dtlz2(n_variables=5, n_objectives=3)
    options = algorithms.nsga3_options()
    options.template.selection.reference_vector_options.number_of_vectors = 21
    options.template.selection.reference_vector_options.lattice_resolution = None
    options.template.termination = CompositeTerminatorOptions(
        terminators=[
            MaxEvaluationsTerminatorOptions(max_evaluations=300),
            MaxGenerationsTerminatorOptions(max_generations=400),
        ],
        mode="any",
    )
    solver, extras = algorithms.emo_constructor(problem=problem, emo_options=options)
    _ = solver()
    generations = int(extras.archive.selections["generation"].max())

    assert generations < 60, generations


@pytest.mark.ea
def test_rvea_adapts_reference_vectors_more_than_once_under_an_evaluation_budget(monkeypatch):
    """Under the evaluation-based strategy adaptation used to happen once and never again."""
    calls = {"n": 0}
    original = RVEASelector._adapt

    def counting(self):
        calls["n"] += 1
        return original(self)

    monkeypatch.setattr(RVEASelector, "_adapt", counting)

    problem = dtlz2(n_variables=5, n_objectives=3)
    options = algorithms.rvea_options()
    options.template.selection.parameter_adaptation_strategy = ParameterAdaptationStrategy.FUNCTION_EVALUATION_BASED
    options.template.selection.reference_vector_options.number_of_vectors = 21
    options.template.selection.reference_vector_options.lattice_resolution = None
    options.template.selection.reference_vector_options.adaptation_frequency = 2
    options.template.termination = MaxEvaluationsTerminatorOptions(max_evaluations=600)
    solver, _ = algorithms.emo_constructor(problem=problem, emo_options=options)
    _ = solver()
    # One initial adaptation plus one every 2 * 21 evaluations across 600.
    assert calls["n"] >= 5, calls["n"]
