"""Reproduction tests for the original XLEMOO article on vehicle crash worthiness."""

import math

import numpy as np
import polars as pl
import pytest

from desdeo.emo.hooks.archivers import Archive
from desdeo.emo.options.algorithms import emo_constructor, xlemoo_options
from desdeo.emo.options.templates import EMOOptions, ReferencePointOptions
from desdeo.explanations.rules import extract_skoped_rules
from desdeo.problem import SimulatorEvaluator
from desdeo.problem.testproblems import vehicle_crashworthiness
from desdeo.tools.generics import EMOResult

REFERENCE_POINT = {"f_1": 1650.0, "f_2": 7.0, "f_3": 0.05}


def _build_xlemoo_runner(seed: int, max_generations: int = 200):
    """Build XLEMOO via the Pydantic path on the vehicle crash problem.

    Returns (runner, extras, learning_operator) so tests can both run the algorithm
    and inspect the learning operator's state afterwards.
    """
    options = xlemoo_options()
    options.template.termination.max_generations = max_generations
    options.template.seed = seed

    options = EMOOptions(
        preference=ReferencePointOptions(preference=REFERENCE_POINT),
        template=options.template,
    )

    runner, extras = emo_constructor(emo_options=options, problem=vehicle_crashworthiness())
    learning_operator = runner.keywords["learning_operator"]
    return runner, extras, learning_operator


def _attach_full_archive(extras) -> Archive:
    """Attach an Archive that retains every evaluation, for tests that need the full history.

    The learning operator no longer holds its own unbounded archive (only H/L groups),
    so tests asking convergence questions about the whole run need to hook one in
    themselves. We attach it post-`emo_constructor`; the publisher dispatches messages
    to whoever's subscribed at notify-time, regardless of when they joined.
    """
    archive = Archive(problem=extras.problem, publisher=extras.publisher)
    extras.publisher.auto_subscribe(archive)
    extras.publisher.register_topics(
        topics=archive.provided_topics[archive.verbosity],
        source=archive.__class__.__name__,
    )
    return archive


@pytest.mark.slow
def test_vehicle_crash_problem_exists():
    """The vehicle crash worthiness problem has the article's variables, objectives, and bounds."""
    problem = vehicle_crashworthiness()

    assert len(problem.variables) == 5
    assert len(problem.objectives) == 3

    for var in problem.variables:
        assert var.lowerbound == 1.0
        assert var.upperbound == 3.0

    expected_ideal = {"f_1": 1600.0, "f_2": 6.0, "f_3": 0.038}
    expected_nadir = {"f_1": 1700.0, "f_2": 12.0, "f_3": 0.30}
    by_symbol = {obj.symbol: obj for obj in problem.objectives}
    for symbol, value in expected_ideal.items():
        assert by_symbol[symbol].ideal == value
    for symbol, value in expected_nadir.items():
        assert by_symbol[symbol].nadir == value


@pytest.mark.slow
def test_vehicle_crash_problem_evaluates():
    """Evaluating at the article's example point reproduces the published outputs."""
    problem = vehicle_crashworthiness()
    evaluator = SimulatorEvaluator(problem)

    out = evaluator.evaluate(
        {"x_1": [1.0], "x_2": [3.0], "x_3": [1.0], "x_4": [1.25473], "x_5": [2.99988]},
        flat=True,
    )

    expected = {"f_1": 1677.23, "f_2": 7.61449, "f_3": 0.068647}
    for symbol, value in expected.items():
        actual = out[symbol].item()
        assert math.isclose(actual, value, rel_tol=1e-2), f"{symbol}={actual}, expected ~{value}"


@pytest.mark.slow
def test_xlemoo_runs_on_vehicle_crash():
    """End-to-end XLEMOO run on the vehicle crash problem with the article's settings."""
    runner, _extras, _ = _build_xlemoo_runner(seed=67)

    result = runner()

    assert isinstance(result, EMOResult)
    assert result.optimal_variables.shape == (50, 5)
    assert result.optimal_outputs.shape[0] == 50

    values = result.optimal_variables.to_numpy()
    assert np.all(values >= 1.0)
    assert np.all(values <= 3.0)

    asf_column = [c for c in result.optimal_outputs.columns if c.startswith("asf")]
    assert asf_column, "no ASF target column in outputs"
    best_asf = float(result.optimal_outputs[asf_column[0]].min())
    assert math.isfinite(best_asf)
    assert best_asf > 0


@pytest.mark.slow
def test_xlemoo_convergence_vehicle_crash():
    """The best ASF improves between the early and late stages of the run.

    XLEMOO is stochastic, so the test only requires improvement in 2 of 3 seeds.
    Attaches a test-only ``Archive`` (every evaluation kept) so we can split early
    vs late generations cleanly — neither the operator's bounded H/L groups nor the
    NonDominatedArchive exposed via ``extras`` retain the full history needed here.
    """
    improved = 0
    for seed in (0, 1, 2):
        runner, extras, _ = _build_xlemoo_runner(seed=seed)
        archive = _attach_full_archive(extras)
        runner()

        assert archive.solutions is not None

        all_solutions: pl.DataFrame = archive.solutions
        asf_column = next(c for c in all_solutions.columns if c.startswith("asf"))

        early = all_solutions.filter(pl.col("generation") <= 20)
        late = all_solutions.filter(pl.col("generation") > 20)
        assert early.height > 0 and late.height > 0

        early_best = float(early[asf_column].min())
        late_best = float(late[asf_column].min())

        if late_best < early_best:
            improved += 1

    assert improved >= 2, f"XLEMOO improved in only {improved}/3 seeds"


@pytest.mark.slow
def test_xlemoo_learning_mode_produces_rules():
    """At least one of a few XLEMOO runs leaves the operator with extracted rules.

    SkopeRules can occasionally yield zero rules on the final H/L split (e.g. when the
    population has converged and the two groups look too similar). Trying a handful of
    seeds checks the implementation can produce rules end-to-end without depending on
    a single stochastic outcome.
    """
    last_count = 0
    for seed in (7, 0, 1):
        runner, _, learning_operator = _build_xlemoo_runner(seed=seed)
        runner()
        assert learning_operator.current_ml_model is not None
        rules, weights = extract_skoped_rules(learning_operator.current_ml_model)
        last_count = len(rules)
        if rules:
            assert len(rules) == len(weights)
            return
    pytest.fail(f"No rules extracted across all seeds (last attempt: {last_count} rules)")
