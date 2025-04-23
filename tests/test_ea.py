"""Tests for Evolutionary Algorithms."""

from contextlib import suppress

import numpy as np
import numpy.testing as npt
import polars as pl
import pytest

from desdeo.emo.hooks.archivers import Archive, FeasibleArchive, NonDominatedArchive
from desdeo.emo.methods.bases import template1
from desdeo.emo.methods.EAs import nsga3, rvea
from desdeo.emo.operators.crossover import (
    SimulatedBinaryCrossover,
    SinglePointBinaryCrossover,
    UniformIntegerCrossover,
    UniformMixedIntegerCrossover,
)
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import (
    LHSGenerator,
    RandomBinaryGenerator,
    RandomGenerator,
    RandomIntegerGenerator,
    RandomMixedInteger,
)
from desdeo.emo.operators.mutation import (
    BinaryFlipMutation,
    BoundedPolynomialMutation,
    IntegerRandomMutation,
    MixedIntegerRandomMutation,
)
from desdeo.emo.operators.selection import (
    ParameterAdaptationStrategy,
    ReferenceVectorOptions,
    RVEASelector,
)
from desdeo.emo.operators.termination import MaxEvaluationsTerminator
from desdeo.problem.testproblems import (
    dtlz2,
    momip_ti2,
    simple_integer_test_problem,
    simple_knapsack,
    simple_knapsack_vectors,
)
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

    norm_non_dom = non_dom_archive.solutions.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    norm_final = results.outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    norm_all = archive.solutions.with_columns(
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
        verbosity=2,
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

    norm = non_dom_archive.solutions.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    assert norm.median() < 1.1
    # assert archive.archive.shape[0] <= 5000 # This test will unfortunately fail because the termination check is done
    # after the evaluation has been done. So, there will always be one more generation than expected.


@pytest.mark.ea
def test_single_point_binary_crossover():
    """Test to check that the single point binary crossover operator works as intended."""
    publisher = Publisher()

    for problem in [simple_knapsack(), simple_knapsack_vectors()]:
        crossover = SinglePointBinaryCrossover(problem=problem, publisher=publisher, seed=0)
        num_vars = len(crossover.variable_symbols)

        population = pl.DataFrame(
            np.vstack((np.ones((5, num_vars)), np.zeros((5, num_vars)))),
            schema=crossover.variable_symbols,
        )

        to_mate = [0, 9, 1, 8, 2, 7, 3, 6, 4, 5]

        result = crossover.do(population=population, to_mate=to_mate)

        assert result.shape == (len(to_mate), num_vars)

        with npt.assert_raises(AssertionError):
            npt.assert_allclose(population, result)

        # test with uneven mating population size as well
        population = pl.DataFrame(
            np.vstack((np.ones((4, num_vars)), np.zeros((3, num_vars)))),
            schema=crossover.variable_symbols,
        )

        to_mate = [0, 2, 1, 3, 6, 4, 5]

        result = crossover.do(population=population, to_mate=to_mate)

        assert result.shape == (len(to_mate), num_vars)

        with npt.assert_raises(AssertionError):
            npt.assert_allclose(population, result)


@pytest.mark.ea
def test_binary_flip_mutation():
    """Test whether the binary flip mutation operator works as intended."""
    publisher = Publisher()

    problem = simple_knapsack()

    # default mutation probability
    mutation = BinaryFlipMutation(problem=problem, publisher=publisher, seed=0)
    num_vars = len(mutation.variable_symbols)

    population = pl.DataFrame(
        np.ones((10, num_vars)),
        schema=mutation.variable_symbols,
    )

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == (len(population), num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    assert 1.0 in result.to_numpy()
    assert 0.0 in result.to_numpy()

    # all bits should flip
    mutation = BinaryFlipMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=1.0)
    num_vars = len(mutation.variable_symbols)

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == (len(population), num_vars)

    npt.assert_allclose(np.zeros((10, num_vars)), result)

    # no bit should flip
    mutation = BinaryFlipMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=0)
    num_vars = len(mutation.variable_symbols)

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == (len(population), num_vars)

    npt.assert_allclose(np.ones((10, num_vars)), result)


@pytest.mark.ea
def test_binary_generation():
    """Test the binary generator."""
    publisher = Publisher()
    n_points = 20

    problem = simple_knapsack()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher)

    generator = RandomBinaryGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0
    )

    population, outputs = generator.do()

    assert population.shape == (n_points, len(problem.get_flattened_variables()))
    assert outputs.shape == (n_points, 3 + 3 + 1)  # three objectives (and targets), one constraint

    problem = simple_knapsack_vectors()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher)

    generator = RandomBinaryGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0
    )

    population, outputs = generator.do()

    assert population.shape == (n_points, len(problem.get_flattened_variables()))
    assert outputs.shape == (
        n_points,
        2 + 2 + 1 + 3,
    )  # two objectives (and targets), one constraint, and three constants?


@pytest.mark.ea
def test_uniform_integer_crossover():
    """Test whether the uniform integer crossover operator works as intended."""
    publisher = Publisher()

    problem = simple_integer_test_problem()

    crossover = UniformIntegerCrossover(problem=problem, publisher=publisher, seed=1)
    num_vars = len(crossover.variable_symbols)

    population = pl.DataFrame(
        crossover.rng.integers(problem.variables[0].lowerbound, problem.variables[0].upperbound, (10, num_vars)),
        schema=crossover.variable_symbols,
    )

    to_mate = [0, 9, 1, 8, 2, 7, 3, 6, 4]

    result = crossover.do(population=population, to_mate=to_mate)

    assert result.shape == (len(to_mate), num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # test with no to_mate
    result = crossover.do(
        population=population,
    )

    assert result.shape == (len(population), num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)


@pytest.mark.ea
def test_integer_random_mutation():
    """Test whether the integer random mutation operator works as intended."""
    publisher = Publisher()

    problem = simple_integer_test_problem()

    # default mutation probability
    mutation = IntegerRandomMutation(problem=problem, publisher=publisher, seed=0)
    num_vars = len(mutation.variable_symbols)

    population = pl.DataFrame(
        mutation.rng.integers(0, 10, size=(10, num_vars), endpoint=True),
        schema=mutation.variable_symbols,
    )

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # zero mutation probability
    mutation = IntegerRandomMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=0.0)

    population = pl.DataFrame(
        mutation.rng.integers(0, 10, size=(10, num_vars), endpoint=True),
        schema=mutation.variable_symbols,
    )

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    npt.assert_allclose(population, result)


@pytest.mark.ea
def test_random_integer_generation():
    """Test the random integer generator."""
    publisher = Publisher()
    n_points = 20

    problem = simple_integer_test_problem()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher)

    generator = RandomIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0
    )

    population, outputs = generator.do()

    assert np.all(population.to_numpy() <= 10)
    assert np.all(population.to_numpy() >= 0)

    assert population.shape == (n_points, len(problem.get_flattened_variables()))
    assert outputs.shape == (n_points, 2 * 5)  # 5 objectives, both min and max


@pytest.mark.ea
def test_template_integer():
    """Test whether creating an EA from components and a template works for integer problems."""
    problem = simple_integer_test_problem()
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=2)

    generator = RandomIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=2
    )

    crossover = UniformIntegerCrossover(problem=problem, publisher=publisher, seed=0)
    mutation = IntegerRandomMutation(problem=problem, publisher=publisher, seed=0)

    selector = RVEASelector(
        problem=problem,
        publisher=publisher,
        parameter_adaptation_strategy=ParameterAdaptationStrategy.FUNCTION_EVALUATION_BASED,
        reference_vector_options=ReferenceVectorOptions(number_of_vectors=20),
        verbosity=2,
    )

    terminator = MaxEvaluationsTerminator(max_evaluations=100, publisher=publisher)

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


@pytest.mark.ea
def test_mixed_integer_generator():
    """Tests that the mixed integer generator works as expected."""
    publisher = Publisher()
    n_points = 20

    problem = momip_ti2()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher)

    generator = RandomMixedInteger(problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0)

    population, outputs = generator.do()

    assert np.all(population.to_numpy() <= 1.0)
    assert np.all(population.to_numpy() >= -1.0)

    assert population.shape == (n_points, len(problem.get_flattened_variables()))
    assert outputs.shape == (n_points, 2 * 2 + 2)  # 2 objectives, both min and max, and two constraints


@pytest.mark.ea
def test_uniform_mixed_integer_crossover():
    """Test whether the uniform mixed-integer crossover operator works as intended."""
    publisher = Publisher()
    n_points = 20

    problem = momip_ti2()

    crossover = UniformMixedIntegerCrossover(problem=problem, publisher=publisher, seed=1)
    num_vars = len(crossover.variable_symbols)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher)
    generator = RandomMixedInteger(problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0)

    population, _ = generator.do()

    to_mate = [0, 9, 1, 8, 2, 7, 3, 6, 4]

    result = crossover.do(population=population, to_mate=to_mate)

    assert result.shape == (len(to_mate), num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # test with no to_mate
    result = crossover.do(
        population=population,
    )

    assert result.shape == (len(population), num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)


@pytest.mark.ea
def test_mixed_integer_random_mutation():
    """Test whether the mixed-integer random mutation operator works as intended."""
    publisher = Publisher()
    n_points = 20

    problem = momip_ti2()

    # default mutation probability
    mutation = MixedIntegerRandomMutation(problem=problem, publisher=publisher, seed=0)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher)
    generator = RandomMixedInteger(problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0)

    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # zero mutation probability
    mutation = MixedIntegerRandomMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=0.0)

    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    npt.assert_allclose(population, result)
