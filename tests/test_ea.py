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
    IBEASelector,
    NSGA2Selector,
    NSGA3Selector,
    ParameterAdaptationStrategy,
    ReferenceVectorOptions,
    RVEASelector,
    _nsga2_crowding_distance_assignment,
)
from desdeo.emo.operators.termination import (
    CompositeTerminator,
    ExternalCheckTerminator,
    MaxEvaluationsTerminator,
    MaxGenerationsTerminator,
)
from desdeo.emo.options.crossover import SimulatedBinaryCrossoverOptions
from desdeo.problem import VariableDomainTypeEnum, VariableTypeEnum
from desdeo.problem.testproblems import (
    dtlz2,
    mixed_variable_dimensions_problem,
    momip_ti2,
    river_pollution_problem,
    simple_integer_test_problem,
    simple_knapsack,
    simple_knapsack_vectors,
    simple_test_problem,
)
from desdeo.tools.message import EvaluatorMessageTopics, IntMessage, TerminatorMessageTopics
from desdeo.tools.patterns import Publisher, Subscriber
from desdeo.tools.utils import repair


@pytest.mark.ea
def test_nsga3():
    """Test whether the NSGA-III algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _publisher = nsga3(problem=problem, n_generations=100)

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front

    assert norm.median() < 1.1


@pytest.mark.ea
def test_rvea():
    """Test whether the RVEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _publisher = rvea(problem=problem, n_generations=100)

    results = solver()

    norm = results.optimal_outputs.with_columns(
        (pl.col("f_1") ** 2 + pl.col("f_2") ** 2 + pl.col("f_3") ** 2).sqrt().alias("norm")
    )["norm"]

    # Assert that most solutions are on the spherical front

    assert norm.median() < 1.1


@pytest.mark.ea
def test_ibea():
    """Test whether the IBEA algorithm can be initialized and run as a whole."""
    problem = dtlz2(n_objectives=3, n_variables=12)
    solver, _publisher = ibea(problem=problem, n_generations=100)

    results = solver()

    norm = results.optimal_outputs.with_columns(
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

    norm_final = results.optimal_outputs.with_columns(
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

    selector = IBEASelector(
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
    with suppress(NotImplementedError):
        solver, _publisher = nsga3_mixed_integer(problem=problem, n_generations=10)
        _ = solver()


@pytest.mark.ea
def test_real_nsga3():
    """Test whether the 'default' NSGA-III variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _publisher = nsga3(problem=problem, n_generations=10)

    _ = solver()


@pytest.mark.ea
def test_mixed_integer_rvea():
    """Test whether the mixed-integer RVEA variant can be initialized and run as a whole."""
    problem = momip_ti2()
    solver, _publisher = rvea_mixed_integer(problem=problem, n_generations=10)

    _ = solver()


@pytest.mark.ea
def test_real_rvea():
    """Test whether the 'default' RVEA variant can be initialized and run as a whole."""
    problem = river_pollution_problem()
    solver, _publisher = rvea(problem=problem, n_generations=10)

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

    population, _outputs = generator.do()

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

    population, _outputs = generator.do()

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

    crossover = LocalCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0)
    num_vars = len(crossover.variable_symbols)

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=10, seed=0, verbosity=1
    )

    population, _outputs = generator.do()

    to_mate = [0, 9, 1, 8, 2]
    offspring = crossover.do(population=population, to_mate=to_mate)

    # An odd sized mating pool is padded with a duplicate parent internally, but the extra offspring
    # that pair produces is dropped, so the operator always returns one offspring per mated parent.
    assert offspring.shape == (len(to_mate), num_vars)

    with npt.assert_raises(AssertionError):
        npt.assert_allclose(population[to_mate], offspring)

    for i in range(len(to_mate)):
        assert not np.allclose(population[to_mate[i]], offspring[i])


"""Every concrete crossover operator, paired with a problem whose variable domain it accepts."""
ALL_CROSSOVERS = [
    (SimulatedBinaryCrossover, "continuous"),
    (BlendAlphaCrossover, "continuous"),
    (SingleArithmeticCrossover, "continuous"),
    (LocalCrossover, "continuous"),
    (BoundedExponentialCrossover, "continuous"),
    (SinglePointBinaryCrossover, "binary"),
    (UniformIntegerCrossover, "integer"),
    (UniformMixedIntegerCrossover, "mixed"),
]

CONTINUOUS_ONLY_CROSSOVERS = [
    SimulatedBinaryCrossover,
    BlendAlphaCrossover,
    SingleArithmeticCrossover,
    LocalCrossover,
    BoundedExponentialCrossover,
]


@pytest.mark.ea
@pytest.mark.parametrize(("crossover_class", "domain"), ALL_CROSSOVERS)
def test_crossover_preserves_population_orientation(crossover_class, domain: str):
    """Test that crossover operators do not transpose a square offspring block.

    `DataFrame.to_numpy` returns an F-contiguous array and `np.zeros_like` preserves that order.
    With as many offspring as variables, `pl.from_numpy` cannot infer the orientation from the
    shape and reads such an array column-wise, which silently transposes the offspring.
    """
    problem = _problem_for(domain)
    variables = problem.get_flattened_variables()
    n_variables = len(variables)
    crossover = crossover_class(problem=problem, publisher=Publisher(), seed=0, verbosity=1)

    # A population of identical individuals. Recombining a parent with itself must reproduce it,
    # whatever the operator does, so any departure is the frame and not the crossover. The values
    # differ between variables, so transposing the block turns these constant columns into
    # constant rows, which no longer match the parent.
    individual = np.array(
        [var.lowerbound if i % 2 == 0 else var.upperbound for i, var in enumerate(variables)], dtype=float
    )
    assert len(set(individual)) > 1, "the test needs an individual that is not the same value repeated"

    for n_rows in (n_variables - 1, n_variables, n_variables + 1):
        parents = pl.DataFrame(np.tile(individual, (n_rows, 1)), schema=[var.symbol for var in variables])

        offspring = crossover.do(population=parents, to_mate=list(range(n_rows)))

        assert offspring.columns == parents.columns
        assert offspring.height == n_rows
        npt.assert_allclose(
            offspring.to_numpy().astype(float),
            np.tile(individual, (n_rows, 1)),
            err_msg=(
                f"{crossover_class.__name__} did not reproduce a population of identical parents "
                f"at {n_rows} offspring x {n_variables} variables"
            ),
        )


@pytest.mark.ea
@pytest.mark.parametrize(("crossover_class", "domain"), ALL_CROSSOVERS)
def test_crossover_state_before_first_do(crossover_class, domain: str):
    """Test that the state of a crossover operator can be queried before it has produced offspring.

    Every `state` implementation guards on the parent population being unset, so the guard must
    see None rather than an attribute that was annotated but never assigned.
    """
    crossover = crossover_class(problem=_problem_for(domain), publisher=Publisher(), seed=0, verbosity=2)

    assert crossover.state() == []
    crossover.notify()  # Must not raise either.


@pytest.mark.ea
@pytest.mark.parametrize(("crossover_class", "domain"), ALL_CROSSOVERS)
@pytest.mark.parametrize("verbosity", [1, 2])
def test_crossover_provided_topics_match_state(crossover_class, domain: str, verbosity: int):
    """Test that the topics a crossover operator advertises are the ones it actually sends.

    A topic that is advertised but never sent leaves a subscriber waiting forever, while one
    that is sent but never advertised makes `Publisher.check_consistency` report a false failure.
    """
    problem = _problem_for(domain)
    crossover = crossover_class(problem=problem, publisher=Publisher(), seed=0, verbosity=verbosity)
    parents = _population(problem, 6)

    crossover.do(population=parents, to_mate=list(range(6)))

    assert {message.topic for message in crossover.state()} == set(crossover.provided_topics[verbosity])


@pytest.mark.ea
@pytest.mark.parametrize("crossover_class", CONTINUOUS_ONLY_CROSSOVERS)
def test_continuous_crossover_rejects_non_continuous_problems(crossover_class):
    """Test that the real-coded crossover operators refuse a problem they cannot handle.

    Blending or averaging parents produces fractional values, which are not valid for integer or
    binary variables, so these operators must reject such a problem rather than silently corrupt it.
    """
    with pytest.raises(ValueError, match="continuous"):
        crossover_class(problem=momip_ti2(), publisher=Publisher(), seed=0, verbosity=1)


@pytest.mark.ea
def test_simulated_binary_crossover_defaults_to_the_truncated_variant():
    """Test that SBX uses the truncated formulation unless asked otherwise.

    The truncated variant is what pymoo, jMetalPy, Platypus and Deb's own NSGA-II code implement,
    so it is the default here too. The untruncated variant, which PlatEMO implements, samples from
    the untruncated density and clips whatever falls outside onto the nearest bound.
    """
    problem = dtlz2(n_objectives=3, n_variables=6)

    assert SimulatedBinaryCrossover(problem=problem, publisher=Publisher(), seed=0, verbosity=1).truncated
    assert SimulatedBinaryCrossoverOptions().truncated
    assert not SimulatedBinaryCrossover(
        problem=problem, publisher=Publisher(), seed=0, verbosity=1, truncated=False
    ).truncated

    # The two variants differ in how they keep the offspring feasible: truncation samples inside
    # the bounds, whereas clipping stacks all the mass that fell outside onto the bound itself.
    # With the parents close to the lower bound and a wide distribution, that shows up as a pile of
    # offspring sitting exactly on the bound.
    symbols = [var.symbol for var in problem.get_flattened_variables()]
    n_pairs = 200
    values = np.empty((2 * n_pairs, len(symbols)))
    values[0::2] = 0.02  # `get_parents` mates consecutive rows, so alternate the two parents
    values[1::2] = 0.12
    parents = pl.DataFrame(values, schema=symbols)

    on_bound = {}
    for truncated in (True, False):
        crossover = SimulatedBinaryCrossover(
            problem=problem,
            publisher=Publisher(),
            seed=0,
            verbosity=1,
            xover_distribution=2,
            truncated=truncated,
        )
        offspring = crossover.do(population=parents, to_mate=list(range(2 * n_pairs))).to_numpy().astype(float)
        assert ((offspring >= 0.0) & (offspring <= 1.0)).all(), "both variants must stay inside the bounds"
        on_bound[truncated] = float(np.mean(np.isclose(offspring, 0.0)))

    assert on_bound[True] == 0.0, "truncation generates offspring inside the bounds, so none sit exactly on one"
    assert on_bound[False] > 0.01, (
        f"clipping should pile offspring onto the bound, but only {on_bound[False]:.3f} landed there"
    )


@pytest.mark.ea
def test_crossover_offspring_count_for_odd_mating_pools():
    """Every crossover operator must return exactly one offspring per mated parent."""
    publisher = Publisher()
    problem = simple_test_problem()
    population = pl.DataFrame(
        np.random.default_rng(0).uniform(0, 10, (10, 2)),
        schema=[var.symbol for var in problem.get_flattened_variables()],
    )

    operators = [
        SimulatedBinaryCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0, truncated=False),
        SimulatedBinaryCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0, truncated=True),
        BlendAlphaCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0),
        SingleArithmeticCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0),
        LocalCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0),
        BoundedExponentialCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0),
    ]

    for crossover in operators:
        for to_mate in ([0, 1, 2, 3], [0, 1, 2, 3, 4]):
            offspring = crossover.do(population=population, to_mate=to_mate)
            assert offspring.height == len(to_mate), (
                f"{type(crossover).__name__} returned {offspring.height} offspring for {len(to_mate)} parents"
            )


@pytest.mark.ea
def test_single_point_binary_crossover_point_range():
    """The crossover point must be able to fall anywhere that actually splits the parents."""
    publisher = Publisher()
    problem = simple_knapsack()
    crossover = SinglePointBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    num_vars = len(crossover.variable_symbols)

    # One all-ones parent mated with one all-zeros parent, so each offspring spells out the
    # crossover point that produced it.
    population = pl.DataFrame(
        np.vstack((np.ones((1, num_vars)), np.zeros((1, num_vars)))), schema=crossover.variable_symbols
    )

    points_seen = set()
    for _ in range(500):
        for row in crossover.do(population=population, to_mate=[0, 1]).to_numpy():
            points_seen.add(int(row.sum()) if row[0] == 1 else num_vars - int(row.sum()))

    # A point of 0 or num_vars would just copy a parent, so the valid points are 1..num_vars - 1.
    # The last gene used to never cross, which left the extreme points unreachable.
    assert points_seen == set(range(1, num_vars))


def test_single_point_binary_crossover_needs_two_variables():
    """A single variable cannot be split, and must fail with a clear message."""
    problem = simple_knapsack()
    crossover = SinglePointBinaryCrossover(problem=problem, publisher=Publisher(), seed=0, verbosity=1)
    crossover.variable_symbols = crossover.variable_symbols[:1]

    population = pl.DataFrame(np.array([[1.0], [0.0]]), schema=crossover.variable_symbols)

    with pytest.raises(ValueError, match="at least two decision variables"):
        crossover.do(population=population, to_mate=[0, 1])


@pytest.mark.ea
@pytest.mark.parametrize("crossover_class", [UniformIntegerCrossover, UniformMixedIntegerCrossover])
def test_uniform_crossover_masks_vary_between_pairs(crossover_class):
    """Each mating pair needs its own mask, otherwise the whole generation shares one column split."""
    publisher = Publisher()
    problem = simple_knapsack()
    crossover = crossover_class(problem=problem, publisher=publisher, seed=0, verbosity=1)
    num_vars = len(crossover.variable_symbols)

    # Alternating all-zero and all-one parents, so every offspring is a readout of its pair's mask.
    n_pairs = 8
    population = pl.DataFrame(
        np.tile(np.array([[0.0] * num_vars, [1.0] * num_vars]), (n_pairs, 1)), schema=crossover.variable_symbols
    )

    offspring = crossover.do(population=population, to_mate=list(range(2 * n_pairs))).to_numpy()
    masks = {tuple(row) for row in offspring[:n_pairs]}

    assert len(masks) > 1, "every pair received the same crossover mask"


@pytest.mark.ea
def test_bounded_exponential_crossover_handles_shared_parent_values():
    """Parents sharing a value on a bound used to yield NaN offspring via a 0/0 span."""
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=5)
    symbols = [var.symbol for var in problem.get_flattened_variables()]

    for seed in range(25):
        crossover = BoundedExponentialCrossover(problem=problem, publisher=publisher, verbosity=1, seed=seed)
        parents = np.full((2, len(symbols)), 0.5)
        parents[:, 0] = 0.0  # both parents pinned to the lower bound
        parents[:, 1] = 1.0  # both parents pinned to the upper bound
        parents[:, 2] = 0.25  # shared value strictly inside the bounds

        offspring = crossover.do(population=pl.DataFrame(parents, schema=symbols), to_mate=[0, 1]).to_numpy()

        assert np.isfinite(offspring).all(), f"non-finite offspring for seed {seed}"
        # A zero span leaves the child no room to move away from the shared parent value.
        npt.assert_allclose(offspring[:, :3], parents[:, :3])


@pytest.mark.ea
def test_bounded_exponential_crossover_is_parent_centric_in_both_orderings():
    """BEX must decay away from each parent whichever way round the pair is stored.

    Thakur, Meghwani and Jalota (2014) derive beta assuming x_i < y_i. Feeding the signed parent
    difference into the exponent inverts the density when x_i > y_i, so the offspring pile up on the
    variable bound instead of around their parent - for roughly half of all decision variables.
    """
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=5)  # every variable is bounded to [0, 1]
    symbols = [var.symbol for var in problem.get_flattened_variables()]
    lower, upper, lam = 0.0, 1.0, 0.3

    near, far = 0.25, 0.75
    n_pairs, repeats = 500, 20

    for first, second in ((near, far), (far, near)):
        crossover = BoundedExponentialCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0, lambda_=lam)
        parents = np.tile(np.array([[first] * len(symbols), [second] * len(symbols)]), (n_pairs, 1))
        children = np.concatenate(
            [
                crossover.do(
                    population=pl.DataFrame(parents, schema=symbols), to_mate=list(range(2 * n_pairs))
                ).to_numpy()[:n_pairs, 0]
                for _ in range(repeats)
            ]
        )

        assert children.min() >= lower and children.max() <= upper, "offspring escaped the variable bounds"

        # The density decays away from the parent and is truncated at the bounds, so a band centred
        # on the parent must hold far more offspring than equally wide bands at the bounds.
        band = 0.05
        at_parent = np.mean(np.abs(children - first) < band)
        at_bounds = np.mean((children - lower < band) | (upper - children < band))
        assert at_parent > at_bounds, (
            f"parents ({first}, {second}): {at_parent:.3f} of offspring landed within {band} of their "
            f"parent but {at_bounds:.3f} landed against a bound; the exponential points the wrong way"
        )


@pytest.mark.ea
def test_single_arithmetic_crossover_changes_one_gene():
    """Single arithmetic crossover blends one gene and leaves the rest of the parent untouched."""
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=6)
    symbols = [var.symbol for var in problem.get_flattened_variables()]

    for seed in range(10):
        crossover = SingleArithmeticCrossover(
            problem=problem, publisher=publisher, xover_probability=1.0, verbosity=1, seed=seed
        )
        parents = np.array([[0.2] * 6, [0.8] * 6])
        offspring = crossover.do(population=pl.DataFrame(parents, schema=symbols), to_mate=[0, 1]).to_numpy()

        for child, parent in zip(offspring, parents, strict=True):
            differing = np.flatnonzero(child != parent)
            assert differing.size == 1, f"expected exactly one blended gene, changed {differing.size}"
            npt.assert_allclose(child[differing], 0.5)


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


"""Every concrete mutation operator, paired with a problem whose variable domain it accepts."""
ALL_MUTATIONS = [
    (BoundedPolynomialMutation, "continuous"),
    (BinaryFlipMutation, "binary"),
    (IntegerRandomMutation, "integer"),
    (MixedIntegerRandomMutation, "mixed"),
    (MPTMutation, "mixed"),
    (NonUniformMutation, "mixed"),
    (PowerMutation, "continuous"),
    (SelfAdaptiveGaussianMutation, "continuous"),
]


def _problem_for(domain: str):
    """Return a test problem whose variable domain a mutation operator accepts."""
    match domain:
        case "continuous":
            return dtlz2(n_objectives=3, n_variables=6)
        case "binary":
            return simple_knapsack()
        case "integer":
            return simple_integer_test_problem()
        case _:
            return momip_ti2()


def _population(problem, n_rows: int) -> pl.DataFrame:
    """Build a population of `n_rows` distinct, in-bounds, integer-feasible individuals."""
    variables = problem.get_flattened_variables()
    lower = np.array([var.lowerbound for var in variables], dtype=float)
    upper = np.array([var.upperbound for var in variables], dtype=float)
    # Evenly spaced inside the box, so that every entry of the population is distinct.
    steps = np.linspace(0.1, 0.9, n_rows * len(variables)).reshape(n_rows, len(variables))
    values = lower + steps * (upper - lower)
    discrete = [var.variable_type in (VariableTypeEnum.binary, VariableTypeEnum.integer) for var in variables]
    values[:, discrete] = np.round(values[:, discrete])
    return pl.DataFrame(values, schema=[var.symbol for var in variables])


@pytest.mark.ea
@pytest.mark.parametrize(("mutation_class", "domain"), ALL_MUTATIONS)
def test_mutation_preserves_population_orientation(mutation_class, domain: str):
    """Test that mutation operators do not transpose a square population.

    `DataFrame.to_numpy` returns an F-contiguous array. For a population with as many
    individuals as variables, `pl.from_numpy` cannot infer the orientation from the shape and
    reads such an array column-wise, which silently transposes the population.
    """
    problem = _problem_for(domain)
    n_variables = len(problem.get_flattened_variables())

    for n_rows in (n_variables - 1, n_variables, n_variables + 1):
        mutation = mutation_class(problem=problem, publisher=Publisher(), seed=0, verbosity=1, mutation_probability=0.0)
        population = _population(problem, n_rows)

        # With a zero mutation probability every operator is the identity.
        result = mutation.do(offsprings=population, parents=population)

        assert result.columns == population.columns
        npt.assert_allclose(
            result.to_numpy().astype(float),
            population.to_numpy().astype(float),
            err_msg=f"{mutation_class.__name__} altered a {n_rows}x{n_variables} population it should have left alone",
        )


@pytest.mark.ea
@pytest.mark.parametrize(("mutation_class", "domain"), ALL_MUTATIONS)
def test_mutation_supports_tensor_variables(mutation_class, domain: str):
    """Test that mutation operators handle problems whose variables are tensors.

    Operators must read bounds and types from the flattened variables, which is what the
    population columns correspond to, rather than from `problem.variables`.
    """
    if domain in ("binary", "integer"):
        pytest.skip(f"{mutation_class.__name__} does not accept the mixed domain of the tensor test problem")

    problem = mixed_variable_dimensions_problem()
    mutation = mutation_class(problem=problem, publisher=Publisher(), seed=0, verbosity=1)
    n_variables = len(problem.get_flattened_variables())
    assert len(problem.variables) < n_variables, "expected a problem whose variables flatten out"

    population = _population(problem, 5)
    result = mutation.do(offsprings=population, parents=population)

    assert result.shape == population.shape
    assert result.columns == population.columns
    # This problem also has variables whose bounds are a single point, which must not divide by zero.
    assert np.isfinite(result.to_numpy().astype(float)).all()


@pytest.mark.ea
@pytest.mark.parametrize(("mutation_class", "domain"), ALL_MUTATIONS)
def test_mutation_respects_bounds_and_integer_domain(mutation_class, domain: str):
    """Test that mutated offspring stay inside the box and keep integer variables integral.

    The templates only apply a repair function after mutation, and that function may be the
    identity, so the operators cannot rely on being cleaned up afterwards.
    """
    if mutation_class is SelfAdaptiveGaussianMutation and domain != "continuous":
        pytest.skip("SelfAdaptiveGaussianMutation is documented as a real-coded operator")

    problem = _problem_for(domain)
    variables = problem.get_flattened_variables()
    lower = np.array([var.lowerbound for var in variables], dtype=float)
    upper = np.array([var.upperbound for var in variables], dtype=float)
    discrete = [var.variable_type in (VariableTypeEnum.binary, VariableTypeEnum.integer) for var in variables]

    mutation = mutation_class(problem=problem, publisher=Publisher(), seed=0, verbosity=1, mutation_probability=1.0)
    population = _population(problem, 10)

    result = mutation.do(offsprings=population, parents=population).to_numpy().astype(float)

    assert np.isfinite(result).all()
    assert (result >= lower - 1e-9).all() and (result <= upper + 1e-9).all(), (
        f"{mutation_class.__name__} produced offspring outside the variable bounds"
    )
    if any(discrete):
        npt.assert_allclose(
            result[:, discrete],
            np.round(result[:, discrete]),
            err_msg=f"{mutation_class.__name__} produced fractional values for integer variables",
        )


@pytest.mark.ea
@pytest.mark.parametrize(("mutation_class", "domain"), ALL_MUTATIONS)
def test_mutation_state_before_first_do(mutation_class, domain: str):
    """Test that the state of a mutation operator can be queried before it has mutated anything.

    Every `state` implementation guards on the offspring being unset, so the guard must see
    None rather than an attribute that was annotated but never assigned.
    """
    mutation = mutation_class(problem=_problem_for(domain), publisher=Publisher(), seed=0, verbosity=2)

    assert mutation.state() == []
    mutation.notify()  # Must not raise either.


@pytest.mark.ea
@pytest.mark.parametrize(("mutation_class", "domain"), ALL_MUTATIONS)
@pytest.mark.parametrize("verbosity", [1, 2])
def test_mutation_provided_topics_match_state(mutation_class, domain: str, verbosity: int):
    """Test that the topics a mutation operator advertises are the ones it actually sends.

    A topic that is advertised but never sent leaves a subscriber waiting forever, while one
    that is sent but never advertised makes `Publisher.check_consistency` report a false failure.
    """
    problem = _problem_for(domain)
    mutation = mutation_class(problem=problem, publisher=Publisher(), seed=0, verbosity=verbosity)
    population = _population(problem, 5)

    mutation.do(offsprings=population, parents=population)

    assert {message.topic for message in mutation.state()} == set(mutation.provided_topics[verbosity])


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
@pytest.mark.parametrize("b", [5.0, 2.5])
def test_non_uniform_mutation_past_max_generations(b: float):
    """Test that the Non-Uniform mutation operator survives outliving its generation budget.

    The decay term is `(1 - t / max_generations) ** b`. Without clamping, `t > max_generations`
    makes the base negative, which overflows the float range for an integral `b` and yields a
    complex number for a fractional one.
    """
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=12)

    mutation = NonUniformMutation(
        problem=problem, publisher=publisher, seed=0, max_generations=10, verbosity=1, b=b, mutation_probability=1.0
    )
    population = pl.DataFrame(
        mutation.rng.uniform(0, 1, size=(20, len(mutation.variable_symbols))),
        schema=mutation.variable_symbols,
    )

    # Simulate a run that went far past the budget the operator was given.
    mutation.update(
        IntMessage(topic=TerminatorMessageTopics.GENERATION, value=40, source="A terminator that kept going.")
    )

    # The mismatch between the operator's budget and the run is reported once, not silently ignored.
    with pytest.warns(UserWarning, match="max_generations"):
        result = mutation.do(offsprings=population, parents=population)

    assert mutation.decay_progress == 1.0
    assert result.shape == population.shape
    values = result.to_numpy().astype(float)
    assert np.isfinite(values).all()
    assert ((values >= 0.0) & (values <= 1.0)).all()

    # The decay has run its course, so the mutation strength is zero rather than unbounded.
    npt.assert_allclose(population, result)


@pytest.mark.ea
def test_non_uniform_mutation_follows_terminator_budget():
    """Test that the Non-Uniform mutation operator picks its budget up from the terminator."""
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=12)

    mutation = NonUniformMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)
    assert mutation.max_generations is None

    # Nothing bounds the run yet, so the mutation stays at full strength.
    assert mutation.decay_progress == 0.0

    source = "A terminator."
    mutation.update(IntMessage(topic=TerminatorMessageTopics.MAX_GENERATIONS, value=50, source=source))
    mutation.update(IntMessage(topic=TerminatorMessageTopics.GENERATION, value=20, source=source))

    assert mutation.decay_progress == pytest.approx(0.4)

    # A generation-based budget wins over an evaluation-based one.
    mutation.update(IntMessage(topic=TerminatorMessageTopics.MAX_EVALUATIONS, value=1000, source=source))
    mutation.update(IntMessage(topic=TerminatorMessageTopics.EVALUATION, value=900, source=source))

    assert mutation.decay_progress == pytest.approx(0.4)


@pytest.mark.ea
def test_non_uniform_mutation_evaluation_based_budget():
    """Test that the Non-Uniform mutation operator decays on evaluations when generations are unbounded.

    `MaxEvaluationsTerminator` does not bound the number of generations, so a generation-based
    schedule has nothing to work with.
    """
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=12)

    mutation = NonUniformMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)

    source = "An evaluation counting terminator."
    mutation.update(IntMessage(topic=TerminatorMessageTopics.MAX_EVALUATIONS, value=1000, source=source))
    mutation.update(IntMessage(topic=TerminatorMessageTopics.EVALUATION, value=250, source=source))
    mutation.update(IntMessage(topic=TerminatorMessageTopics.GENERATION, value=9999, source=source))

    assert mutation.decay_progress == pytest.approx(0.25)

    # The budget can be overshot, since the check happens after the evaluations have been made.
    mutation.update(IntMessage(topic=TerminatorMessageTopics.EVALUATION, value=1200, source=source))

    assert mutation.decay_progress == 1.0


@pytest.mark.ea
def test_non_uniform_mutation_with_evaluation_based_termination():
    """Test that an EA with Non-Uniform mutation runs to completion under an evaluation budget.

    With `MaxEvaluationsTerminator` the number of generations is not known in advance, and the
    population size is not constant, so the generation counter cannot be predicted from the
    evaluation budget.
    """
    publisher = Publisher()
    problem = dtlz2(n_objectives=3, n_variables=12)
    repair_func = repair(
        lower_bounds={v.symbol: v.lowerbound for v in problem.get_flattened_variables()},
        upper_bounds={v.symbol: v.upperbound for v in problem.get_flattened_variables()},
    )

    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    crossover = SimulatedBinaryCrossover(problem=problem, publisher=publisher, seed=0, verbosity=1)
    mutation = NonUniformMutation(problem=problem, publisher=publisher, seed=0, verbosity=1)
    selector = RVEASelector(
        problem=problem,
        publisher=publisher,
        verbosity=2,
        parameter_adaptation_strategy=ParameterAdaptationStrategy.FUNCTION_EVALUATION_BASED,
    )
    generator = RandomGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=selector.reference_vectors.shape[0],
        seed=0,
        verbosity=1,
    )
    terminator = MaxEvaluationsTerminator(2000, publisher=publisher)

    components = [evaluator, generator, crossover, mutation, selector, terminator]
    [publisher.auto_subscribe(x) for x in components]
    [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]

    assert publisher.check_consistency()[0]

    result = template1(
        evaluator=evaluator,
        crossover=crossover,
        mutation=mutation,
        generator=generator,
        selection=selector,
        terminator=terminator,
        repair=repair_func,
    )

    # The run outlived any horizon guessed from the nominal population size, but decayed correctly.
    assert mutation.current_generation > 1
    assert mutation.decay_progress <= 1.0
    variables = result.optimal_variables.to_numpy().astype(float)
    assert np.isfinite(variables).all()


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
    mutated = mutation.do(offsprings=population, parents=population)

    # Ensure shape consistency
    assert mutated.shape == population.shape
    assert mutation.step_sizes.shape == (population.shape[0], population.shape[1])

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

    mutated = mutation.do(offsprings=population, parents=population)

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

    population, _outputs = generator.do()

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
                crossover = LocalCrossover(problem=problem, publisher=publisher, verbosity=1, seed=0)
            case _:
                raise ValueError(f"Unknown crossover type: {crossover}")

        selector = NSGA3Selector(
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
            template1(
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
@pytest.mark.fixme
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

        selector = NSGA3Selector(
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
            template1(
                evaluator=evaluator,
                crossover=crossover,
                mutation=mutation,
                generator=generator,
                selection=selector,
                terminator=terminator,
                repair=repair_func,
            )
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

    # We no longer notify the terminator from the generator. The generator calls the evaluator, which calls the
    # terminator.
    # publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])
    # assert terminator.current_evaluations == 100

    for _ in range(100):
        if not terminator.check():
            publisher.notify([IntMessage(topic=EvaluatorMessageTopics.NEW_EVALUATIONS, value=57, source="test")])

    assert terminator.current_evaluations >= 1000
    assert terminator.current_evaluations < 1057  # The maximum can unfortunately be exceeded
    assert terminator.check() is True


def test_composite_terminator():
    """Test the CompositeTerminator with different modes."""
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
    # Composite indicator should get max from children
    assert composite.max_generations == 10
    assert composite.max_evaluations == 1000

    # publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])
    # assert composite.current_evaluations == 100

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

    # publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])
    # assert composite.current_evaluations == 100

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

    # publisher.notify([IntMessage(topic=GeneratorMessageTopics.NEW_EVALUATIONS, value=100, source="test")])
    # assert composite.current_evaluations == 100

    for _ in range(100):
        if not composite.check():
            publisher.notify([IntMessage(topic=EvaluatorMessageTopics.NEW_EVALUATIONS, value=200, source="test")])
        else:
            break

    assert composite.current_generation > term1.max_generations
    assert composite.current_evaluations >= term2.max_evaluations

    # Make sure that creating composite terminator fails if multiple terminators of the same type are added
    with pytest.raises(ValueError, match="All terminators must be unique"):
        CompositeTerminator([term1, term2, term1], publisher, mode="any")


def test_external_terminator():
    """Test the ExternalCheckTerminator."""

    class ExternCheck:
        """Pretend this is an external check."""

        def __init__(self):
            self.value = False

        def check(self):
            """If true, the termination condition is met."""
            return self.value

    publisher = Publisher()
    checker = ExternCheck()
    term = ExternalCheckTerminator(checker.check, publisher)

    for i in range(1, 100):
        if i == 50:
            checker.value = True
        if term.check():
            break

    assert term.current_generation == 51


@pytest.mark.ea
def test_nsga2_selection():
    """Tests the NSGA2 selection operator."""
    population_size = 100
    publisher = Publisher()

    seed = 0
    n_vars = 10
    n_objs = 3
    problem = dtlz2(n_vars, n_objs)

    crossover = SimulatedBinaryCrossover(
        problem=problem, seed=seed, verbosity=2, publisher=publisher, xover_probability=0.9, xover_distribution=20
    )
    mutation = BoundedPolynomialMutation(
        problem=problem,
        seed=seed,
        verbosity=2,
        publisher=publisher,
        mutation_probability=1 / n_vars,
        distribution_index=20,
    )
    selector = NSGA2Selector(
        problem=problem, verbosity=2, publisher=publisher, population_size=population_size, seed=seed
    )
    scalar_selection = TournamentSelection(
        winner_size=population_size, verbosity=2, publisher=publisher, tournament_size=2, seed=seed
    )
    evaluator = EMOEvaluator(problem=problem, publisher=publisher, verbosity=1)
    generator = RandomGenerator(
        problem=problem, evaluator=evaluator, publisher=publisher, n_points=population_size, seed=seed, verbosity=1
    )

    components = [selector, evaluator, generator, scalar_selection, crossover, mutation]
    [publisher.auto_subscribe(x) for x in components]
    [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]

    # first iteration
    solutions, outputs = generator.do()
    offspring = pl.DataFrame(
        schema=solutions.schema,
    )
    offspring_outputs = pl.DataFrame(
        schema=outputs.schema,
    )
    solutions, outputs = selector.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))

    parents, _ = scalar_selection.do((solutions, outputs))
    offspring = crossover.do(population=parents)
    offspring = mutation.do(offspring, solutions)
    offspring_outputs = evaluator.evaluate(offspring)

    # second iteration
    solutions, outputs = selector.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))

    parents, _ = scalar_selection.do((solutions, outputs))
    offspring = crossover.do(population=parents)
    offspring = mutation.do(offspring, solutions)
    offspring_outputs = evaluator.evaluate(offspring)


@pytest.mark.ea
def test_nsga2_selection_dealing_with_boundaries():
    """Tests the NSGA2 selection operator and that it deals with boundaries as expected."""
    population_size = 4
    publisher = Publisher()

    seed = 0
    n_vars = 10
    n_objs = 3
    problem = dtlz2(n_vars, n_objs)

    selector = NSGA2Selector(
        problem=problem, verbosity=2, publisher=publisher, population_size=population_size, seed=seed
    )

    publisher.auto_subscribe(selector)
    publisher.register_topics(selector.provided_topics[selector.verbosity], selector.__class__.__name__)

    # only boundaries in pop
    f_data_pop = {
        "f_1_min": [1.0, 0.0, 0.0],
        "f_2_min": [0.0, 1.0, 0.0],
        "f_3_min": [0.0, 0.0, 1.0],
    }
    f_data_off = {
        "f_1_min": [2.0, 3.0, 3.0, 2.5],
        "f_2_min": [3.0, 2.0, 3.0, 2.5],
        "f_3_min": [3.0, 3.0, 2.0, 2.5],
    }

    x_data_pop = {f"x_{i}": [0.0] * 3 for i in range(1, n_vars + 1)}
    x_data_off = {f"x_{i}": [1.0] * 4 for i in range(1, n_vars + 1)}

    population = (pl.DataFrame(x_data_pop), pl.DataFrame(f_data_pop))
    offspring = (pl.DataFrame(x_data_off), pl.DataFrame(f_data_off))

    res = selector.do(population, offspring)

    f_expected_pop = {
        "f_1_min": [1.0, 0.0, 0.0, 3.0],
        "f_2_min": [0.0, 1.0, 0.0, 3.0],
        "f_3_min": [0.0, 0.0, 1.0, 2.0],
    }

    assert res[1].to_dict(as_series=False) == f_expected_pop


@pytest.mark.ea
def test_nsga2_crowding():
    """Tests the NSGA2 crowding distance computation."""
    # First and last solution on the boundary
    front = np.array(
        [
            [-3.5, 4.5, 3.8],
            [-2.2, 3.6, 3.0],
            [-1.1, 2.7, 2.4],
            # Crowded boys!
            [-0.5, 2.0, 2.1],
            [-0.3, 1.8, 2.0],
            [-0.1, 1.6, 1.9],
            [0.1, 1.4, 1.8],
            # end crowded
            [1.0, 0.7, 1.2],
            [2.4, -0.1, 0.5],
            [4.0, -1.5, -0.8],
        ]
    )

    f_mins = np.min(front, axis=0)
    f_maxs = np.max(front, axis=0)

    distances = _nsga2_crowding_distance_assignment(front, f_mins, f_maxs)

    # boundary points should always be included
    assert all(distances[0] > distances[1:-1])
    assert all(distances[-1] > distances[1:-1])

    # crowded solutions should have worse value than non-crowded
    # the 4 solutions in the 'middle' are considered crowded
    for i_crowded in range(3, 7):
        # compare to sparsely distributed first three solutions
        assert all(distances[i_crowded] < distances[0:3])
        # compare to sparsely distributed last three solutions
        assert all(distances[i_crowded] < distances[7:-1])

    # Three boundary points in the middle
    front = np.array([[0.5, 0.5, 0.5], [0.0, 1.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 0.0], [0.5, 0.5, 0.5]])

    f_mins = np.min(front, axis=0)
    f_maxs = np.max(front, axis=0)

    distances = _nsga2_crowding_distance_assignment(front, f_mins, f_maxs)

    assert all(distances[1:4] == np.inf)
    assert distances[0] < np.inf
    assert distances[-1] < np.inf
