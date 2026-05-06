"""Tests for the ElitistSelection scalar selection operator.

ElitistSelection lives in `desdeo.emo.operators.scalar_selection` and replaces
the previous ASFSelector. It ranks the combined ``(decision_variables, outputs)``
tuple by a single output column (lower is better) and keeps the top
``winner_size`` rows.
"""

import numpy as np
import polars as pl
import pytest

from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator
from desdeo.emo.operators.scalar_selection import ElitistSelection
from desdeo.problem.testproblems import dtlz2
from desdeo.tools.patterns import Publisher
from desdeo.tools.scalarization import add_asf_nondiff


def _make_problem_with_asf(n_objectives: int = 3, n_variables: int = 5):
    """Build a DTLZ2 problem with an ASF scalarization attached."""
    problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)
    reference_point = {f"f_{i}": 0.5 for i in range(1, n_objectives + 1)}
    problem, asf_symbol = add_asf_nondiff(problem, symbol="asf", reference_point=reference_point)
    return problem, asf_symbol


def _combined_population(problem, asf_symbol, *, seed: int = 0, n_points: int = 50):
    """Generate two LHS populations and stack them into one combined ``(decvars, outputs)``."""
    publisher = Publisher()
    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = LHSGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=seed, verbosity=1
    )
    decvars_a, outputs_a = generator.do()
    decvars_b, outputs_b = generator.do()
    return decvars_a.vstack(decvars_b), outputs_a.vstack(outputs_b)


@pytest.mark.ea
def test_elitist_selection_selects_correct_number():
    """ElitistSelection returns exactly winner_size rows from the combined pool."""
    problem, asf_symbol = _make_problem_with_asf()
    decvars, outputs = _combined_population(problem, asf_symbol, seed=0)

    publisher = Publisher()
    selector = ElitistSelection(
        publisher=publisher,
        verbosity=1,
        winner_size=50,
        target_column=asf_symbol,
    )

    selected_decvars, selected_outputs = selector.do((decvars, outputs))

    assert selected_decvars.shape[0] == 50
    assert selected_outputs.shape[0] == 50


@pytest.mark.ea
def test_elitist_selection_selects_best():
    """Every kept individual has an ASF value <= the worst rejected individual's."""
    problem, asf_symbol = _make_problem_with_asf()
    decvars, outputs = _combined_population(problem, asf_symbol, seed=1)

    publisher = Publisher()
    selector = ElitistSelection(
        publisher=publisher,
        verbosity=1,
        winner_size=50,
        target_column=asf_symbol,
    )

    _, selected_outputs = selector.do((decvars, outputs))

    sorted_vals = np.sort(outputs[asf_symbol].to_numpy())
    rejected_vals = sorted_vals[50:]
    selected_vals = selected_outputs[asf_symbol].to_numpy()

    assert selected_vals.max() <= rejected_vals.min()


@pytest.mark.ea
def test_elitist_selection_deterministic():
    """Running do() twice with the same input produces identical results."""
    problem, asf_symbol = _make_problem_with_asf()
    decvars, outputs = _combined_population(problem, asf_symbol, seed=2)

    publisher = Publisher()
    selector = ElitistSelection(
        publisher=publisher,
        verbosity=1,
        winner_size=50,
        target_column=asf_symbol,
    )

    decvars1, outputs1 = selector.do((decvars, outputs))
    decvars2, outputs2 = selector.do((decvars, outputs))

    assert decvars1.equals(decvars2)
    assert outputs1.equals(outputs2)


@pytest.mark.ea
def test_elitist_selection_with_explicit_fitness_overrides_target_column():
    """Passing ``fitness`` directly overrides the target column lookup."""
    problem, asf_symbol = _make_problem_with_asf()
    decvars, outputs = _combined_population(problem, asf_symbol, seed=3, n_points=10)

    publisher = Publisher()
    selector = ElitistSelection(
        publisher=publisher,
        verbosity=1,
        winner_size=5,
        target_column=asf_symbol,
    )

    # Inverted fitness: smallest score now corresponds to the largest ASF, so the
    # selection should pick the rows that the target_column path would reject.
    inverted = -outputs[asf_symbol].to_numpy()
    _, selected_outputs = selector.do((decvars, outputs), fitness=inverted)

    sorted_vals = np.sort(outputs[asf_symbol].to_numpy())
    selected_vals = selected_outputs[asf_symbol].to_numpy()
    # Selected via inverted fitness should be the top-5 worst original ASF.
    assert selected_vals.min() >= sorted_vals[-6]


@pytest.mark.ea
def test_elitist_selection_returns_polars_dataframe():
    """Selected outputs/decvars are polars DataFrames so downstream EA components compose."""
    problem, asf_symbol = _make_problem_with_asf()
    decvars, outputs = _combined_population(problem, asf_symbol, seed=4)

    publisher = Publisher()
    selector = ElitistSelection(
        publisher=publisher,
        verbosity=1,
        winner_size=20,
        target_column=asf_symbol,
    )

    selected_decvars, selected_outputs = selector.do((decvars, outputs))

    assert isinstance(selected_decvars, pl.DataFrame)
    assert isinstance(selected_outputs, pl.DataFrame)
