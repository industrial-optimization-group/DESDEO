"""Tests for the XLEMOO learning-mode operator."""

import numpy as np
import polars as pl
import pytest

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
    """Construct a DTLZ2 problem with ASF and the operators needed to warm up the learning operator."""
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

    return {
        "problem": problem,
        "publisher": publisher,
        "evaluator": evaluator,
        "generator": generator,
        "crossover": crossover,
        "mutation": mutation,
        "selector": selector,
        "asf_symbol": asf_symbol,
        "population_size": population_size,
    }


def _build_operator(components: dict) -> LearningModeOperator:
    """Construct a `LearningModeOperator` from the test components."""
    return LearningModeOperator(
        problem=components["problem"],
        selector=components["selector"],
        publisher=components["publisher"],
        seed=0,
    )


def _run_darwinian(components: dict, operator: LearningModeOperator, generations: int) -> None:
    """Wire publisher subscriptions, then run ``generations`` Darwinian iterations of an ElitistSelection EA.

    The ``operator`` is subscribed before the loop runs so it receives the same VERBOSE_OUTPUTS messages
    that an archive would, populating its H- and L-groups as the population evolves.
    """
    terminator = MaxGenerationsTerminator(generations, publisher=components["publisher"])
    subs: list[Subscriber] = [
        components["evaluator"],
        components["generator"],
        components["crossover"],
        components["mutation"],
        components["selector"],
        operator,
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


@pytest.mark.ea
def test_learning_mode_returns_decision_dataframe():
    """`LearningModeOperator.do()` returns just the instantiated decision-variable DataFrame."""
    components = _build_components()
    operator = _build_operator(components)
    _run_darwinian(components, operator, generations=20)

    result = operator.do()

    assert isinstance(result, pl.DataFrame)
    # Same columns as the problem's decision variables, in the same order.
    assert list(result.columns) == [v.symbol for v in components["problem"].get_flattened_variables()]


@pytest.mark.ea
def test_learning_mode_returns_expected_row_count():
    """The instantiated DataFrame is sized according to ``instantiation_factor * winner_size``."""
    components = _build_components(population_size=30)
    operator = _build_operator(components)
    _run_darwinian(components, operator, generations=20)

    decision_vars = operator.do()

    expected = int(operator.instantiation_factor * components["selector"].winner_size)
    # `instantiate_from_ruleset` may round to a slightly different total; allow ±5.
    assert abs(decision_vars.height - expected) <= 5


@pytest.mark.ea
def test_learning_mode_stores_ml_model():
    """`current_ml_model` is set after a successful learning iteration."""
    components = _build_components()
    operator = _build_operator(components)
    _run_darwinian(components, operator, generations=20)

    assert operator.current_ml_model is None
    operator.do()
    assert operator.current_ml_model is not None


@pytest.mark.ea
def test_learning_mode_returns_none_before_any_update():
    """Before any VERBOSE_OUTPUTS has been observed, the operator returns ``None`` instead of crashing."""
    components = _build_components()
    operator = _build_operator(components)
    # Subscribe but never publish anything to the operator.
    components["publisher"].auto_subscribe(operator)
    components["publisher"].register_topics(
        topics=operator.provided_topics[operator.verbosity],
        source=operator.__class__.__name__,
    )

    assert operator.do() is None


@pytest.mark.ea
def test_hl_groups_separated_by_target():
    """Every individual in the H-group has a strictly better (lower) ASF than every L-group individual."""
    components = _build_components()
    operator = _build_operator(components)
    _run_darwinian(components, operator, generations=20)

    asf = components["asf_symbol"]

    assert operator.h_group is not None and operator.h_group.height > 0
    assert operator.l_group is not None and operator.l_group.height > 0

    h_vals = operator.h_group[asf].to_numpy()
    l_vals = operator.l_group[asf].to_numpy()

    assert h_vals.max() <= l_vals.min()


@pytest.mark.ea
def test_learning_mode_instantiated_within_bounds():
    """All decision-variable values returned by the operator stay inside the problem bounds."""
    components = _build_components()
    operator = _build_operator(components)
    _run_darwinian(components, operator, generations=20)

    decision_vars = operator.do()
    assert decision_vars is not None
    values = decision_vars.to_numpy()

    for i, var in enumerate(components["problem"].get_flattened_variables()):
        assert np.all(values[:, i] >= var.lowerbound)
        assert np.all(values[:, i] <= var.upperbound)


@pytest.mark.ea
def test_learning_mode_groups_bounded_by_budget():
    """H- and L-groups never exceed their declared budgets, even after many generations."""
    components = _build_components(population_size=30)
    operator = _build_operator(components)
    _run_darwinian(components, operator, generations=50)

    assert operator.h_group is not None
    assert operator.l_group is not None
    assert operator.h_group.height <= operator.h_size
    assert operator.l_group.height <= operator.l_size
