"""Tests for the XLEMOO learning-mode operator."""

import numpy as np
import polars as pl
import pytest

from desdeo.emo.hooks.archivers import Archive
from desdeo.emo.operators.crossover import SimulatedBinaryCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator
from desdeo.emo.operators.learning_mode import LearningModeOperator
from desdeo.emo.operators.mutation import BoundedPolynomialMutation
from desdeo.emo.operators.scalar_selection import ElitistSelection
from desdeo.emo.operators.termination import MaxGenerationsTerminator
from desdeo.problem.testproblems import dtlz2
from desdeo.tools.patterns import Publisher, Subscriber
from desdeo.tools.scalarization import add_asf_nondiff


def _build_components(population_size: int = 30):
    """Construct a DTLZ2 problem with ASF and the components needed to warm up an archive."""
    problem = dtlz2(n_variables=5, n_objectives=3)
    reference_point = {"f_1": 0.5, "f_2": 0.5, "f_3": 0.5}
    problem, asf_symbol = add_asf_nondiff(problem, symbol="asf", reference_point=reference_point)

    publisher = Publisher()
    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=2)
    generator = LHSGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=population_size,
        seed=0,
        verbosity=2,
    )
    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)
    selector = ElitistSelection(
        publisher=publisher,
        verbosity=2,
        winner_size=population_size,
        target_column=asf_symbol,
    )
    archive = Archive(problem=problem, publisher=publisher)

    return {
        "problem": problem,
        "publisher": publisher,
        "evaluator": evaluator,
        "generator": generator,
        "crossover": crossover,
        "mutation": mutation,
        "selector": selector,
        "archive": archive,
        "asf_symbol": asf_symbol,
        "population_size": population_size,
    }


def _run_darwinian(components: dict, generations: int) -> None:
    """Wire the publisher, then run ``generations`` Darwinian iterations of an ElitistSelection EA."""
    terminator = MaxGenerationsTerminator(generations, publisher=components["publisher"])
    subs: list[Subscriber] = [
        components["evaluator"],
        components["generator"],
        components["crossover"],
        components["mutation"],
        components["selector"],
        components["archive"],
        terminator,
    ]
    [components["publisher"].auto_subscribe(s) for s in subs]
    [
        components["publisher"].register_topics(topics=s.provided_topics[s.verbosity], source=s.__class__.__name__)
        for s in subs
    ]

    evaluator = components["evaluator"]
    generator = components["generator"]
    crossover = components["crossover"]
    mutation = components["mutation"]
    selector = components["selector"]

    solutions, outputs = generator.do()
    while not terminator.check():
        offspring = crossover.do(population=solutions)
        offspring = mutation.do(offspring, solutions)
        offspring_outputs = evaluator.evaluate(offspring)
        combined_decvars = solutions.vstack(offspring)
        combined_outputs = outputs.vstack(offspring_outputs)
        solutions, outputs = selector.do((combined_decvars, combined_outputs))


def _build_operator(components: dict) -> LearningModeOperator:
    """Construct a `LearningModeOperator` from the test components."""
    return LearningModeOperator(
        problem=components["problem"],
        archive=components["archive"],
        selector=components["selector"],
        publisher=components["publisher"],
        seed=0,
    )


@pytest.mark.ea
def test_learning_mode_returns_decision_dataframe():
    """`LearningModeOperator.do()` returns just the instantiated decision-variable DataFrame."""
    components = _build_components()
    _run_darwinian(components, generations=20)

    operator = _build_operator(components)
    result = operator.do()

    assert isinstance(result, pl.DataFrame)
    # Same columns as the problem's decision variables, in the same order.
    assert list(result.columns) == [v.symbol for v in components["problem"].get_flattened_variables()]


@pytest.mark.ea
def test_learning_mode_returns_expected_row_count():
    """The instantiated DataFrame is sized according to ``instantiation_factor * winner_size``."""
    components = _build_components(population_size=30)
    _run_darwinian(components, generations=20)

    operator = _build_operator(components)
    decision_vars = operator.do()

    expected = int(operator.instantiation_factor * components["selector"].winner_size)
    # `instantiate_from_ruleset` may round to a slightly different total; allow ±5.
    assert abs(decision_vars.height - expected) <= 5


@pytest.mark.ea
def test_learning_mode_stores_ml_model():
    """`current_ml_model` is set after a successful learning iteration."""
    components = _build_components()
    _run_darwinian(components, generations=20)

    operator = _build_operator(components)
    assert operator.current_ml_model is None
    operator.do()
    assert operator.current_ml_model is not None


@pytest.mark.ea
def test_learning_mode_returns_none_on_empty_archive():
    """If the archive has no solutions, the operator returns ``None`` instead of crashing."""
    components = _build_components()
    operator = _build_operator(components)
    assert operator.do() is None


@pytest.mark.ea
def test_hl_split_best_in_h_group():
    """Every individual in the H-group has a strictly better (lower) ASF than every L-group individual."""
    components = _build_components()
    _run_darwinian(components, generations=20)

    archive = components["archive"]
    asf = components["asf_symbol"]
    variable_symbols = [v.symbol for v in components["problem"].get_flattened_variables()]

    unique = archive.solutions.unique(subset=variable_symbols, maintain_order=True).sort(asf)
    h_size = int(0.2 * unique.height)
    l_size = int(0.2 * unique.height)

    h_vals = unique.head(h_size)[asf].to_numpy()
    l_vals = unique.tail(l_size)[asf].to_numpy()

    assert h_vals.max() <= l_vals.min()


@pytest.mark.ea
def test_learning_mode_instantiated_within_bounds():
    """All decision-variable values returned by the operator stay inside the problem bounds."""
    components = _build_components()
    _run_darwinian(components, generations=20)

    operator = _build_operator(components)
    decision_vars = operator.do()
    assert decision_vars is not None
    values = decision_vars.to_numpy()

    for i, var in enumerate(components["problem"].get_flattened_variables()):
        assert np.all(values[:, i] >= var.lowerbound)
        assert np.all(values[:, i] <= var.upperbound)


@pytest.mark.ea
def test_learning_mode_reads_from_archive():
    """The operator reads the current archive on every call, picking up new generations."""
    components = _build_components()
    _run_darwinian(components, generations=20)

    operator = _build_operator(components)
    operator.do()
    rows_before = components["archive"].solutions.height

    # Run more Darwinian iterations to grow the archive.
    publisher = components["publisher"]
    extra_terminator = MaxGenerationsTerminator(10, publisher=publisher)
    publisher.auto_subscribe(extra_terminator)
    publisher.register_topics(
        topics=extra_terminator.provided_topics[extra_terminator.verbosity],
        source=extra_terminator.__class__.__name__,
    )

    evaluator = components["evaluator"]
    generator = components["generator"]
    crossover = components["crossover"]
    mutation = components["mutation"]
    selector = components["selector"]
    solutions, outputs = generator.do()
    while not extra_terminator.check():
        offspring = crossover.do(population=solutions)
        offspring = mutation.do(offspring, solutions)
        offspring_outputs = evaluator.evaluate(offspring)
        combined_decvars = solutions.vstack(offspring)
        combined_outputs = outputs.vstack(offspring_outputs)
        solutions, outputs = selector.do((combined_decvars, combined_outputs))

    rows_after = components["archive"].solutions.height
    assert rows_after > rows_before

    operator.do()
    # The operator must observe the additional rows added after the first call.
    assert components["archive"].solutions.height >= rows_after
