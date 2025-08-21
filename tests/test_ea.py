"""Tests for Evolutionary Algorithms."""

from contextlib import suppress

import numpy as np
import numpy.testing as npt
import polars as pl
import pytest

from desdeo.emo.hooks.archivers import Archive, FeasibleArchive, NonDominatedArchive
from desdeo.emo.methods.EAs import ibea, nsga3, nsga3_mixed_integer, rvea, rvea_mixed_integer
from desdeo.emo.methods.templates import template1, template2
from desdeo.emo.operators.crossover import (
    BlendAlphaCrossover,
    BoundedExponentialCrossover,
    LocalCrossover,
    SimulatedBinaryCrossover,
    SingleArithmeticCrossover,
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
    RandomMixedIntegerGenerator,
)
from desdeo.emo.operators.mutation import (
    BinaryFlipMutation,
    BoundedPolynomialMutation,
    IntegerRandomMutation,
    MixedIntegerRandomMutation,
    MPTMutation,
    NonUniformMutation,
    PowerMutation,
    SelfAdaptiveGaussianMutation,
)
from desdeo.emo.operators.scalar_selection import TournamentSelection
from desdeo.emo.operators.selection import (
    IBEA_Selector,
    NSGAIII_select,
    ParameterAdaptationStrategy,
    ReferenceVectorOptions,
    RVEASelector,
)
from desdeo.emo.operators.termination import MaxEvaluationsTerminator, MaxGenerationsTerminator, CompositeTerminator
from desdeo.problem import VariableDomainTypeEnum
from desdeo.problem.testproblems import (
    dtlz2,
    momip_ti2,
    river_pollution_problem,
    simple_integer_test_problem,
    simple_knapsack,
    simple_knapsack_vectors,
    simple_test_problem,
)
from desdeo.tools.message import IntMessage, TerminatorMessageTopics, GeneratorMessageTopics, EvaluatorMessageTopics
from desdeo.tools.patterns import Publisher, Subscriber
from desdeo.tools.utils import repair


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
def test_ibea():
    """Test whether the IBEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, publisher = ibea(problem=problem, n_generations=100)

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

    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

    population = pl.DataFrame(
        np.vstack((np.zeros((10, 12)), np.zeros((10, 12)) + 1)), schema=[f"x_{i + 1}" for i in range(12)]
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

        evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)

        generator = LHSGenerator(
            problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=1
        )

        solutions, outputs = generator.do()

        assert solutions.shape == (10, n_variables)
        assert outputs.shape == (10, n_obj * 2 + 1)  # k objectives, k targets, and 1 extra function

        generator = RandomGenerator(
            problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=1
        )

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
def test_template1():
    """Test whether creating an EA from components and a template works."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=2)

    generator = LHSGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=2
    )

    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

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

    assert publisher.check_consistency()[0], "Subscribers are subscribing to unregistered topics."

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
def test_template2():
    """Test whether creating an EA from components and a template works."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=2)

    generator = LHSGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=2
    )

    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

    selector = IBEA_Selector(
        problem=problem,
        publisher=publisher,
        population_size=10,
        verbosity=2,
    )

    terminator = MaxEvaluationsTerminator(max_evaluations=500, publisher=publisher)

    non_dom_archive = NonDominatedArchive(problem=problem, publisher=publisher)
    archive = Archive(problem=problem, publisher=publisher)
    scalar_selector = TournamentSelection(publisher=publisher, winner_size=10, verbosity=0)

    components: list[Subscriber] = [
        evaluator,
        generator,
        crossover,
        mutation,
        selector,
        terminator,
        non_dom_archive,
        archive,
        scalar_selector,
    ]

    [publisher.auto_subscribe(component) for component in components]
    [
        publisher.register_topics(
            topics=component.provided_topics[component.verbosity], source=component.__class__.__name__
        )
        for component in components
    ]

    assert publisher.check_consistency()[0], "Subscribers are subscribing to unregistered topics."

    results = template2(
        evaluator=evaluator,
        generator=generator,
        crossover=crossover,
        mutation=mutation,
        selection=selector,
        terminator=terminator,
        mate_selection=scalar_selector,
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
        crossover = SinglePointBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
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
    mutation = BinaryFlipMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)
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
    mutation = BinaryFlipMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=1.0, verbosity=1)
    num_vars = len(mutation.variable_symbols)

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == (len(population), num_vars)

    npt.assert_allclose(np.zeros((10, num_vars)), result)

    # no bit should flip
    mutation = BinaryFlipMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=0, verbosity=1)
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

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)

    generator = RandomBinaryGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
    )

    population, outputs = generator.do()

    assert population.shape == (n_points, len(problem.get_flattened_variables()))
    assert outputs.shape == (n_points, 3 + 3 + 1)  # three objectives (and targets), one constraint

    problem = simple_knapsack_vectors()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)

    generator = RandomBinaryGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
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

    crossover = UniformIntegerCrossover(problem=problem, publisher=publisher, seed=1, verbosity=1)
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
    mutation = IntegerRandomMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)
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
    mutation = IntegerRandomMutation(
        problem=problem, publisher=publisher, seed=0, mutation_probability=0.0, verbosity=1
    )

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

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)

    generator = RandomIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
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

    crossover = UniformIntegerCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    mutation = IntegerRandomMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

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

    assert publisher.check_consistency(), "Subscribers are subscribing to unregistered topics."

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

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)

    generator = RandomMixedIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
    )

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

    crossover: UniformMixedIntegerCrossover = UniformMixedIntegerCrossover(
        problem=problem, publisher=publisher, seed=1, verbosity=1
    )
    num_vars = len(crossover.variable_symbols)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomMixedIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
    )

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
    mutation = MixedIntegerRandomMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomMixedIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
    )

    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # zero mutation probability
    mutation = MixedIntegerRandomMutation(
        problem=problem, publisher=publisher, seed=0, mutation_probability=0.0, verbosity=1
    )

    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    npt.assert_allclose(population, result)


@pytest.mark.ea
def test_template_mixed_integer():
    """Test whether creating an EA from components and a template works for mixed-integer problems."""
    problem = momip_ti2()
    publisher = Publisher()

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=2)

    generator = RandomMixedIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=200, seed=0, verbosity=2
    )

    crossover = UniformMixedIntegerCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    mutation = MixedIntegerRandomMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

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

    assert publisher.check_consistency(), "Subscribers are subscribing to unregistered topics."

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
def test_mixed_integer_nsga3():
    """Test whether the mixed-integer NSGA-III variant can be initialized and run as a whole."""
    problem = momip_ti2()
    solver, publisher = nsga3_mixed_integer(problem=problem, n_generations=10)

    _ = solver()


@pytest.mark.ea
def test_real_nsga3():
    """Test whether the 'default' NSGA-III variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, publisher = nsga3(problem=problem, n_generations=10)

    _ = solver()


@pytest.mark.ea
def test_mixed_integer_rvea():
    """Test whether the mixed-integer RVEA variant can be initialized and run as a whole."""
    problem = momip_ti2()
    solver, publisher = rvea_mixed_integer(problem=problem, n_generations=10)

    _ = solver()


@pytest.mark.ea
def test_real_rvea():
    """Test whether the 'default' RVEA variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, publisher = rvea(problem=problem, n_generations=10)

    _ = solver()


@pytest.mark.ea
def test_blend_alpha_crossover():
    """Test whether the BLX-alpha (blend-alpha) crossover operator works as intended."""
    publisher = Publisher()
    problem = simple_test_problem()
    # problem must be continuous
    assert problem.variable_domain is VariableDomainTypeEnum.continuous

    # create operator
    crossover = BlendAlphaCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0)
    num_vars = len(crossover.variable_symbols)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=1
    )

    population, outputs = generator.do()

    # pick a custom mating order (odd-length to test padding)
    to_mate = [0, 9, 1, 8, 2]
    offspring = crossover.do(population=population, to_mate=to_mate)

    assert offspring.shape == (len(to_mate), num_vars)
    # offspring must differ from parents
    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, offspring)


@pytest.mark.ea
def test_single_arithmetic_crossover():
    """Tests the single arithmetic crossover operator."""
    publisher = Publisher()
    problem = simple_test_problem()
    assert problem.variable_domain is VariableDomainTypeEnum.continuous

    crossover = SingleArithmeticCrossover(
        problem=problem, publisher=publisher, xover_probability=1.0, verbosity=1, seed=0
    )
    num_vars = len(crossover.variable_symbols)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=1
    )

    population, outputs = generator.do()

    to_mate = [0, 9, 1, 8, 2]
    offspring = crossover.do(population=population, to_mate=to_mate)

    assert offspring.shape == (len(to_mate), num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population[to_mate], offspring)

    for i in range(len(to_mate)):
        assert not np.allclose(population[to_mate[i]], offspring[i])


@pytest.mark.ea
def test_local_crossover():
    """Tests the local crossover operator."""
    publisher = Publisher()
    problem = simple_test_problem()
    assert problem.variable_domain is VariableDomainTypeEnum.continuous

    crossover = LocalCrossover(problem=problem, publisher=publisher, xover_probability=1.0, verbosity=1, seed=0)
    num_vars = len(crossover.variable_symbols)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=1
    )

    population, outputs = generator.do()

    to_mate = [0, 9, 1, 8, 2]
    offspring = crossover.do(population=population, to_mate=to_mate)

    expected_len = len(to_mate) if len(to_mate) % 2 == 0 else len(to_mate) + 1
    assert offspring.shape == (expected_len, num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population[to_mate], offspring)

    for i in range(len(to_mate)):
        assert not np.allclose(population[to_mate[i]], offspring[i])


@pytest.mark.ea
def test_mpt_mutation():
    """Test whether the MPT mutation operator works as intended."""
    publisher = Publisher()
    n_points = 20

    problem = momip_ti2()

    # default mutation probability
    mutation = MPTMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomMixedIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
    )

    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # zero mutation probability
    mutation = MPTMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=0.0, verbosity=1)

    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    npt.assert_allclose(population, result)


@pytest.mark.ea
def test_non_uniform_mutation():
    """Test whether the Non-Uniform mutation operator works as intended."""
    publisher = Publisher()
    n_points = 20

    problem = momip_ti2()

    # default mutation probability
    mutation = NonUniformMutation(problem=problem, publisher=publisher, seed=0, max_generations=100, verbosity=1)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomMixedIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
    )

    population, _ = generator.do()

    mutation.update(
        IntMessage(
            topic=TerminatorMessageTopics.GENERATION,
            value=10,  # Simulate that we are at generation 10
            source="Just trust me.",
        )
    )
    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # zero mutation probability
    mutation = NonUniformMutation(
        problem=problem, publisher=publisher, seed=0, mutation_probability=0.0, max_generations=100, verbosity=1
    )

    mutation.update(
        IntMessage(
            topic=TerminatorMessageTopics.GENERATION,
            value=20,  # Simulate that we are at generation 20
            source="It came to me in a dream.",
        )
    )
    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape

    npt.assert_allclose(population, result)


@pytest.mark.ea
def test_self_adaptive_gaussian_mutation():
    """Test whether the self-adaptive Gaussian mutation operator works as intended."""
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=12)

    mutation = SelfAdaptiveGaussianMutation(problem=problem, publisher=publisher, seed=42, verbosity=1)
    num_vars = len(mutation.variable_symbols)

    # Create a dummy population
    population = pl.DataFrame(
        mutation.rng.uniform(0, 1, size=(10, num_vars)),
        schema=mutation.variable_symbols,
    )

    # Perform mutation
    mutated, step_sizes = mutation.do(offsprings=population, parents=population)

    # Ensure shape consistency
    assert mutated.shape == population.shape
    assert step_sizes.shape == (population.shape[0], population.shape[1])

    # Should not be exactly equal due to mutations
    with pytest.raises(AssertionError):
        npt.assert_allclose(mutated.to_numpy(), population.to_numpy())

    # Mutation with probability = 0.0
    mutation = SelfAdaptiveGaussianMutation(
        problem=problem, publisher=publisher, seed=42, mutation_probability=0.0, verbosity=1
    )

    population = pl.DataFrame(
        mutation.rng.uniform(0, 1, size=(10, num_vars)),
        schema=mutation.variable_symbols,
    )

    mutated, step_sizes = mutation.do(offsprings=population, parents=population)

    # No change expected
    npt.assert_allclose(mutated.to_numpy(), population.to_numpy())


@pytest.mark.ea
def test_power_mutation_operator():
    """Test whether the power mutation operator works as intended."""
    publisher = Publisher()
    n_points = 20

    problem = momip_ti2()

    # default mutation probability with power mutation
    mutation = PowerMutation(problem=problem, publisher=publisher, seed=0, p=5, verbosity=1)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomMixedIntegerGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
    )

    population, _ = generator.do()

    result = mutation.do(offsprings=population, parents=population)

    # Ensure shape is preserved
    assert result.shape == population.shape

    # Ensure some mutation has occurred (not identical to original)
    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, result)

    # mutation probability = 0 → no mutation should happen
    mutation = PowerMutation(problem=problem, publisher=publisher, seed=0, mutation_probability=0.0, p=5, verbosity=1)

    population, _ = generator.do()
    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape
    npt.assert_allclose(population, result)


@pytest.mark.ea
def test_bounded_exponential_crossover():
    """Test whether the bounded exponential crossover (BEX) operator works as intended."""
    publisher = Publisher()
    problem = simple_test_problem()
    # Make sure the problem is continuous
    assert problem.variable_domain is VariableDomainTypeEnum.continuous

    # create operator
    crossover = BoundedExponentialCrossover(problem=problem, publisher=publisher, lambda_=1.0, verbosity=1, seed=0)
    num_vars = len(crossover.variable_symbols)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=1
    )

    population, outputs = generator.do()

    # pick a custom mating order (odd-length to test padding)
    to_mate = [0, 9, 1, 8, 2]
    offspring = crossover.do(population=population, to_mate=to_mate)

    assert offspring.shape == (len(to_mate), num_vars)
    # offspring must differ from parents
    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population, offspring)


@pytest.mark.slow
@pytest.mark.ea
def test_crossover_in_ea():
    """Test whether the crossover operators can be used in an EA."""
    xovers = ["sbx", "bex", "blend", "single_arithmetic", "local"]

    for xover_name in xovers:
        publisher = Publisher()
        problem = dtlz2(n_objectives=3, n_variables=12)

        evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)

        match xover_name:
            case "sbx":
                crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
            case "bex":
                crossover = BoundedExponentialCrossover(
                    problem=problem, publisher=publisher, lambda_=1.0, verbosity=1, seed=0
                )
            case "blend":
                crossover = BlendAlphaCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0)
            case "single_arithmetic":
                crossover = SingleArithmeticCrossover(
                    problem=problem, publisher=publisher, xover_probability=1.0, verbosity=1, seed=0
                )
            case "local":
                crossover = LocalCrossover(
                    problem=problem, publisher=publisher, xover_probability=1.0, verbosity=1, seed=0
                )
            case _:
                raise ValueError(f"Unknown crossover type: {crossover}")

        selector = NSGAIII_select(
            problem=problem,
            publisher=publisher,
            verbosity=2,
        )

        n_points = selector.reference_vectors.shape[0]

        generator = RandomGenerator(
            problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
        )

        mutation = BoundedPolynomialMutation(
            problem=problem,
            publisher=publisher,
            seed=0,
            verbosity=1,
        )

        terminator = MaxGenerationsTerminator(
            30,
            publisher=publisher,
        )

        components = [evaluator, generator, crossover, mutation, selector, terminator]
        [publisher.auto_subscribe(x) for x in components]
        [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]

        try:
            results = template1(
                evaluator=evaluator,
                crossover=crossover,
                mutation=mutation,
                generator=generator,
                selection=selector,
                terminator=terminator,
            )
        except Exception as e:
            pytest.fail(f"Failed to run EA with crossover {crossover}: {e}")


@pytest.mark.slow
@pytest.mark.ea
def test_mutation_in_ea():
    """Test whether the mutation operators can be used in an EA."""
    mutations = ["bpm", "num", "power", "SAGM"]
    for mut in mutations:
        publisher = Publisher()
        problem = dtlz2(n_objectives=3, n_variables=12)
        repair_func = repair(
            lower_bounds={v.symbol: v.lowerbound for v in problem.get_flattened_variables()},
            upper_bounds={v.symbol: v.upperbound for v in problem.get_flattened_variables()},
        )

        evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
        crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)

        selector = NSGAIII_select(
            problem=problem,
            publisher=publisher,
            verbosity=2,
        )

        n_points = selector.reference_vectors.shape[0]

        generator = RandomGenerator(
            problem=problem, evaluator=evaluator, publisher=publisher, n_points=n_points, seed=0, verbosity=1
        )

        match mut:
            case "bpm":
                mutation = BoundedPolynomialMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)
            case "num":
                mutation = NonUniformMutation(
                    problem=problem, publisher=publisher, seed=0, max_generations=30, verbosity=1
                )
            case "power":
                mutation = PowerMutation(problem=problem, publisher=publisher, seed=0, p=5, verbosity=1)
            case "SAGM":
                mutation = SelfAdaptiveGaussianMutation(problem=problem, publisher=publisher, seed=42, verbosity=1)
            case _:
                raise ValueError(f"Unknown mutation type: {mut}")

        terminator = MaxGenerationsTerminator(
            30,
            publisher=publisher,
        )

        components = [evaluator, generator, crossover, mutation, selector, terminator]
        [publisher.auto_subscribe(x) for x in components]
        [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]

        try:
            results = template1(
                evaluator=evaluator,
                crossover=crossover,
                mutation=mutation,
                generator=generator,
                selection=selector,
                terminator=terminator,
                repair=repair_func,
            )
            print(results)
        except Exception as e:
            pytest.fail(f"Failed to run EA with mutation {mut}: {e}")


def test_max_gen_terminator():
    """Test the MaxGenerationsTerminator."""
    publisher = Publisher()
    terminator = MaxGenerationsTerminator(100, publisher)
    publisher.auto_subscribe(terminator)

    assert terminator.current_generation == 1
    assert terminator.max_generations == 100

    for _ in range(1000):
        if terminator.check():  # Increments current_generation
            break

    assert terminator.current_generation == 101
    assert terminator.check() is True


def test_max_eval_terminator():
    """Test the MaxEvaluationsTerminator."""
    publisher = Publisher()
    terminator = MaxEvaluationsTerminator(1000, publisher)
    publisher.auto_subscribe(terminator)

    assert terminator.current_evaluations == 0
    assert terminator.max_evaluations == 1000

    publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])
    assert terminator.current_evaluations == 100

    for _ in range(100):
        if not terminator.check():
            publisher.notify([IntMessage(topic=EvaluatorMessageTopics.NEW_EVALUATIONS, value=57, source="test")])

    assert terminator.current_evaluations >= 1000
    assert terminator.current_evaluations < 1057  # The maximum can unfortunately be exceeded
    assert terminator.check() is True

def test_composite_terminator():

    # Test that the check works for MaxGenerationsTerminator with "any"
    publisher = Publisher()
    term1 = MaxGenerationsTerminator(10, publisher)
    term2 = MaxEvaluationsTerminator(1000, publisher)
    composite = CompositeTerminator([term1, term2], publisher, mode="any")
    publisher.auto_subscribe(term1)
    publisher.auto_subscribe(term2)
    publisher.auto_subscribe(composite)

    assert composite.current_generation == 1
    assert composite.current_evaluations == 0
    assert term1.max_generations == 10
    assert term2.max_evaluations == 1000

    publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])

    assert composite.current_evaluations == 100

    for _ in range(100):
        if not composite.check():
            publisher.notify([IntMessage(topic=EvaluatorMessageTopics.NEW_EVALUATIONS, value=57, source="test")])
        else:
            break

    assert composite.current_generation == 11
    assert composite.current_evaluations < term2.max_evaluations

    # Test that the check works for MaxEvaluationsTerminator with "any"
    publisher = Publisher()
    term1 = MaxGenerationsTerminator(10, publisher)
    term2 = MaxEvaluationsTerminator(1000, publisher)
    composite = CompositeTerminator([term1, term2], publisher, mode="any")
    publisher.auto_subscribe(term1)
    publisher.auto_subscribe(term2)
    publisher.auto_subscribe(composite)

    assert composite.current_generation == 1
    assert composite.current_evaluations == 0
    assert term1.max_generations == 10
    assert term2.max_evaluations == 1000

    publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])

    assert composite.current_evaluations == 100

    for _ in range(100):
        if not composite.check():
            publisher.notify([IntMessage(topic=EvaluatorMessageTopics.NEW_EVALUATIONS, value=200, source="test")])
        else:
            break

    assert composite.current_generation < term1.max_generations
    assert composite.current_evaluations >= term2.max_evaluations

    # Test that check works for "all"
    publisher = Publisher()
    term1 = MaxGenerationsTerminator(10, publisher)
    term2 = MaxEvaluationsTerminator(1000, publisher)
    composite = CompositeTerminator([term1, term2], publisher, mode="all")
    publisher.auto_subscribe(term1)
    publisher.auto_subscribe(term2)
    publisher.auto_subscribe(composite)

    assert composite.current_generation == 1
    assert composite.current_evaluations == 0
    assert term1.max_generations == 10
    assert term2.max_evaluations == 1000

    publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])

    assert composite.current_evaluations == 100

    for _ in range(100):
        if not composite.check():
            publisher.notify([IntMessage(topic=EvaluatorMessageTopics.NEW_EVALUATIONS, value=200, source="test")])
        else:
            break

    assert composite.current_generation > term1.max_generations
    assert composite.current_evaluations >= term2.max_evaluations
