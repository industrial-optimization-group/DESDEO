"""Tests for the ASF-based selection operator."""

import numpy as np
import polars as pl
import pytest

from desdeo.emo.methods.templates import template1
from desdeo.emo.operators.crossover import SimulatedBinaryCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator
from desdeo.emo.operators.mutation import BoundedPolynomialMutation
from desdeo.emo.operators.selection import ASFSelector
from desdeo.emo.operators.termination import MaxGenerationsTerminator
from desdeo.problem.testproblems import dtlz2
from desdeo.tools.generics import EMOResult
from desdeo.tools.patterns import Publisher, Subscriber
from desdeo.tools.scalarization import add_asf_nondiff


def _make_problem_with_asf(n_objectives: int = 3, n_variables: int = 5):
    """Build a DTLZ2 problem with an ASF scalarization attached."""
    problem = dtlz2(n_variables=n_variables, n_objectives=n_objectives)
    reference_point = {f"f_{i}": 0.5 for i in range(1, n_objectives + 1)}
    problem, asf_symbol = add_asf_nondiff(problem, symbol="asf", reference_point=reference_point)
    return problem, asf_symbol


@pytest.mark.ea
def test_asf_selector_selects_correct_number():
    """ASFSelector returns exactly population_size rows from the combined pool."""
    problem, asf_symbol = _make_problem_with_asf()
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = LHSGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=50, seed=0, verbosity=1
    )

    parents, parent_outputs = generator.do()
    offspring, offspring_outputs = generator.do()

    selector = ASFSelector(
        problem=problem,
        publisher=publisher,
        population_size=50,
        target_column=asf_symbol,
        verbosity=1,
    )

    selected, selected_outputs = selector.do(
        parents=(parents, parent_outputs), offsprings=(offspring, offspring_outputs)
    )

    assert selected.shape[0] == 50
    assert selected_outputs.shape[0] == 50


@pytest.mark.ea
def test_asf_selector_selects_best():
    """Selected individuals all have ASF values <= worst ASF in the rejected pool."""
    problem, asf_symbol = _make_problem_with_asf()
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = LHSGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=50, seed=1, verbosity=1
    )

    parents, parent_outputs = generator.do()
    offspring, offspring_outputs = generator.do()

    selector = ASFSelector(
        problem=problem,
        publisher=publisher,
        population_size=50,
        target_column=asf_symbol,
        verbosity=1,
    )

    _, selected_outputs = selector.do(parents=(parents, parent_outputs), offsprings=(offspring, offspring_outputs))

    all_outputs = parent_outputs.vstack(offspring_outputs)
    all_vals = np.sort(all_outputs[asf_symbol].to_numpy())
    rejected_vals = all_vals[50:]

    selected_vals = selected_outputs[asf_symbol].to_numpy()

    assert selected_vals.max() <= rejected_vals.min()


@pytest.mark.ea
def test_asf_selector_deterministic():
    """Running do() twice with the same input produces identical results."""
    problem, asf_symbol = _make_problem_with_asf()
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = LHSGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=50, seed=2, verbosity=1
    )

    parents, parent_outputs = generator.do()
    offspring, offspring_outputs = generator.do()

    selector = ASFSelector(
        problem=problem,
        publisher=publisher,
        population_size=50,
        target_column=asf_symbol,
        verbosity=1,
    )

    selected1, outputs1 = selector.do(parents=(parents, parent_outputs), offsprings=(offspring, offspring_outputs))
    selected2, outputs2 = selector.do(parents=(parents, parent_outputs), offsprings=(offspring, offspring_outputs))

    assert selected1.equals(selected2)
    assert outputs1.equals(outputs2)


@pytest.mark.ea
def test_asf_selector_in_template1():
    """ASFSelector runs end-to-end inside template1 and improves the best ASF value."""
    problem, asf_symbol = _make_problem_with_asf(n_objectives=3, n_variables=5)
    publisher = Publisher()
    population_size = 30

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=2)
    generator = LHSGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=population_size,
        seed=3,
        verbosity=2,
    )
    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=3, verbosity=1)
    mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=3, verbosity=1)
    selector = ASFSelector(
        problem=problem,
        publisher=publisher,
        population_size=population_size,
        target_column=asf_symbol,
        verbosity=2,
    )
    terminator = MaxGenerationsTerminator(20, publisher=publisher)

    components: list[Subscriber] = [evaluator, generator, crossover, mutation, selector, terminator]
    [publisher.auto_subscribe(c) for c in components]
    [publisher.register_topics(topics=c.provided_topics[c.verbosity], source=c.__class__.__name__) for c in components]

    _initial_solutions, initial_outputs = generator.do()
    initial_best = initial_outputs[asf_symbol].to_numpy().min()

    # Re-create generator so template1's first generator.do() returns a fresh population.
    generator = LHSGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=population_size,
        seed=3,
        verbosity=2,
    )
    publisher.auto_subscribe(generator)
    publisher.register_topics(
        topics=generator.provided_topics[generator.verbosity], source=generator.__class__.__name__
    )

    result = template1(
        evaluator=evaluator,
        generator=generator,
        crossover=crossover,
        mutation=mutation,
        selection=selector,
        terminator=terminator,
    )

    assert isinstance(result, EMOResult)
    assert isinstance(result.optimal_outputs, pl.DataFrame)

    final_best = result.optimal_outputs[asf_symbol].to_numpy().min()
    assert final_best < initial_best
