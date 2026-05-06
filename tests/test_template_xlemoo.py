"""Tests for the template_xlemoo Darwinian/Learning loop."""

import polars as pl
import pytest

from desdeo.emo import xlemoo_options
from desdeo.emo.hooks.archivers import Archive
from desdeo.emo.methods.templates import template_xlemoo
from desdeo.emo.operators.crossover import SimulatedBinaryCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator
from desdeo.emo.operators.learning_mode import LearningModeOperator
from desdeo.emo.operators.mutation import BoundedPolynomialMutation
from desdeo.emo.operators.scalar_selection import ElitistSelection
from desdeo.emo.operators.termination import MaxGenerationsTerminator
from desdeo.emo.options.algorithms import emo_constructor
from desdeo.emo.options.templates import EMOOptions, ReferencePointOptions
from desdeo.problem.testproblems import dtlz2
from desdeo.tools.generics import EMOResult
from desdeo.tools.patterns import Publisher, Subscriber
from desdeo.tools.scalarization import add_asf_nondiff


def _build_components(
    population_size: int,
    max_generations: int,
):
    problem = dtlz2(n_variables=5, n_objectives=3)
    problem, asf_symbol = add_asf_nondiff(problem, symbol="asf", reference_point={"f_1": 0.5, "f_2": 0.5, "f_3": 0.5})

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
    terminator = MaxGenerationsTerminator(max_generations, publisher=publisher)
    archive = Archive(problem=problem, publisher=publisher)

    learning_operator = LearningModeOperator(
        problem=problem,
        archive=archive,
        evaluator=evaluator,
        selector=selector,
        seed=0,
    )

    components: list[Subscriber] = [evaluator, generator, crossover, mutation, selector, terminator, archive]
    [publisher.auto_subscribe(c) for c in components]
    [publisher.register_topics(topics=c.provided_topics[c.verbosity], source=c.__class__.__name__) for c in components]

    return {
        "problem": problem,
        "publisher": publisher,
        "evaluator": evaluator,
        "generator": generator,
        "crossover": crossover,
        "mutation": mutation,
        "selector": selector,
        "terminator": terminator,
        "archive": archive,
        "learning_operator": learning_operator,
        "asf_symbol": asf_symbol,
    }


@pytest.mark.ea
def test_template_xlemoo_runs_to_completion():
    """`template_xlemoo` returns an EMOResult and the archive collects multi-generation data."""
    comps = _build_components(population_size=30, max_generations=63)

    result = template_xlemoo(
        evaluator=comps["evaluator"],
        crossover=comps["crossover"],
        mutation=comps["mutation"],
        generator=comps["generator"],
        selection=comps["selector"],
        learning_operator=comps["learning_operator"],
        terminator=comps["terminator"],
        n_darwin_per_cycle=20,
        n_learning_per_cycle=1,
    )

    assert isinstance(result, EMOResult)
    assert isinstance(result.optimal_outputs, pl.DataFrame)

    archive_solutions = comps["archive"].solutions
    assert archive_solutions is not None
    assert int(archive_solutions["generation"].max()) > 1


@pytest.mark.ea
def test_template_xlemoo_darwinian_only():
    """With `n_learning_per_cycle=0`, the Learning operator is never invoked."""
    comps = _build_components(population_size=30, max_generations=20)

    result = template_xlemoo(
        evaluator=comps["evaluator"],
        crossover=comps["crossover"],
        mutation=comps["mutation"],
        generator=comps["generator"],
        selection=comps["selector"],
        learning_operator=comps["learning_operator"],
        terminator=comps["terminator"],
        n_darwin_per_cycle=20,
        n_learning_per_cycle=0,
    )

    assert isinstance(result, EMOResult)
    assert comps["learning_operator"].current_ml_model is None


@pytest.mark.ea
def test_template_xlemoo_mode_switching_count():
    """With short Darwinian cycles, Learning mode runs at least once and trains the model."""
    comps = _build_components(population_size=30, max_generations=33)

    template_xlemoo(
        evaluator=comps["evaluator"],
        crossover=comps["crossover"],
        mutation=comps["mutation"],
        generator=comps["generator"],
        selection=comps["selector"],
        learning_operator=comps["learning_operator"],
        terminator=comps["terminator"],
        n_darwin_per_cycle=10,
        n_learning_per_cycle=1,
    )

    assert comps["learning_operator"].current_ml_model is not None


@pytest.mark.ea
def test_template_xlemoo_via_pydantic():
    """The Pydantic preset constructor returns a runnable XLEMOO that produces an EMOResult."""
    options = xlemoo_options()
    # Override generation budget so the test runs quickly.
    options.template.termination.max_generations = 50
    options.template.n_darwin_per_cycle = 20
    options.template.n_learning_per_cycle = 1

    options = EMOOptions(
        preference=ReferencePointOptions(preference={"f_1": 0.5, "f_2": 0.5, "f_3": 0.5}),
        template=options.template,
    )

    problem = dtlz2(n_variables=5, n_objectives=3)
    runner, _extras = emo_constructor(emo_options=options, problem=problem)

    result = runner()
    assert isinstance(result, EMOResult)
