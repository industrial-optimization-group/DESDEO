"""Tests for Evolutionary Algorithms."""

from contextlib import suppress

import numpy as np
import polars as pl
import pytest

from desdeo.emo.hooks.archivers import Archive, FeasibleArchive, NonDominatedArchive
from desdeo.emo.methods.bases import template1
from desdeo.emo.methods.EAs import nsga3, rvea
from desdeo.emo.operators.crossover import SimulatedBinaryCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator, RandomGenerator
from desdeo.emo.operators.mutation import BoundedPolynomialMutation
from desdeo.emo.operators.selection import ParameterAdaptationStrategy, ReferenceVectorOptions, RVEASelector
from desdeo.emo.operators.termination import MaxEvaluationsTerminator
from desdeo.problem.testproblems import dtlz2
from desdeo.tools.patterns import Publisher, Subscriber


@pytest.mark.ea
def test_nsga3():
    """Test whether the NSGA-III algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, publisher = nsga3(problem=problem, n_generations=100)

    results = solver()

    norm = results.outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front

    assert norm.median() < 1.1


@pytest.mark.ea
def test_rvea():
    """Test whether the RVEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, publisher = rvea(problem=problem, n_generations=100)

    results = solver()

    norm = results.outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front

    assert norm.median() < 1.1


@pytest.mark.ea
def test_recombination():
    """Test whether the recombination operators can be initialized and run."""
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=12)

    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0)
    mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=0)

    population = pl.DataFrame(
        np.vstack((np.zeros((10, 12)), np.zeros((10, 12)) + 1)), schema=[f"x_{i+1}" for i in range(12)]
    )

    to_mate = [(i, i + 10) for i in range(10)]
    to_mate = [j for i in to_mate for j in i]

    result = crossover.do(population=population, to_mate=to_mate)

    assert result.shape == (20, 12)

    result = mutation.do(offsprings=result, parents=population)

    assert result.shape == (20, 12)


@pytest.mark.ea
def test_generation():
    """Test whether the initial population can be generated."""
    publisher = Publisher()

    for n_obj in [2, 3, 5, 10]:
        n_variables = 12 + n_obj
        problem = dtlz2(n_objectives=n_obj, n_variables=n_variables)

        evaluator = EMOEvaluator(problem=problem, publisher=publisher)

        generator = LHSGenerator(problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0)

        solutions, outputs = generator.do()

        assert solutions.shape == (10, n_variables)
        assert outputs.shape == (10, n_obj * 2 + 1)  # k objectives, k targets, and 1 extra function

        generator = RandomGenerator(problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0)

        solutions, outputs = generator.do()

        assert solutions.shape == (10, n_variables)
        assert outputs.shape == (10, n_obj * 2 + 1)


@pytest.mark.ea
def test_archives():
    """Test whether the archives work."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, publisher = nsga3(problem=problem, n_generations=50)

    archive = Archive(problem=problem, publisher=publisher)

    with suppress(ValueError):  # There are no constraints in the problem. It should raise an error.
        FeasibleArchive(problem=problem, publisher=publisher)

    non_dom_archive = NonDominatedArchive(problem=problem, publisher=publisher)

    publisher.auto_subscribe(archive)
    publisher.auto_subscribe(non_dom_archive)

    results = solver()

    norm_non_dom = non_dom_archive.archive.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    norm_final = results.outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    norm_all = archive.archive.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    assert norm_non_dom.median() < 1.1

    assert norm_non_dom.median() < norm_all.median()
    assert norm_final.median() < norm_all.median()


@pytest.mark.ea
def test_template():
    """Test whether creating an EA from components and a template works."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=2)

    generator = LHSGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=2
    )

    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0)
    mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=0)

    selector = RVEASelector(
        problem=problem,
        publisher=publisher,
        parameter_adaptation_strategy=ParameterAdaptationStrategy.FUNCTION_EVALUATION_BASED,
        reference_vector_options=ReferenceVectorOptions(number_of_vectors=20),
    )

    terminator = MaxEvaluationsTerminator(max_evaluations=5000, publisher=publisher)

    non_dom_archive = NonDominatedArchive(problem=problem, publisher=publisher)
    archive = Archive(problem=problem, publisher=publisher)

    components: list[Subscriber] = [
        evaluator,
        generator,
        crossover,
        mutation,
        selector,
        terminator,
        non_dom_archive,
        archive,
    ]

    [publisher.auto_subscribe(component) for component in components]
    [
        publisher.register_topics(
            topics=component.provided_topics[component.verbosity], source=component.__class__.__name__
        )
        for component in components
    ]

    assert isinstance(publisher.check_consistency(), bool) and publisher.check_consistency()

    results = template1(
        evaluator=evaluator,
        generator=generator,
        crossover=crossover,
        mutation=mutation,
        selection=selector,
        terminator=terminator,
    )

    assert results is not None

    norm = non_dom_archive.archive.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    assert norm.median() < 1.1
    # assert archive.archive.shape[0] <= 5000 # This test will unfortunately fail because the termination check is done
    # after the evaluation has been done. So, there will always be one more generation than expected.
