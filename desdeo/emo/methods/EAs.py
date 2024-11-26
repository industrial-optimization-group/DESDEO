"""Implements common evolutionary algorithms for multi-objective optimization."""

from collections.abc import Callable
from functools import partial

from desdeo.emo.methods.bases import EMOResult, template1
from desdeo.emo.operators.crossover import SimulatedBinaryCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator
from desdeo.emo.operators.mutation import BoundedPolynomialMutation
from desdeo.emo.operators.selection import NSGAIII_select, ReferenceVectorOptions, RVEASelector
from desdeo.emo.operators.termination import MaxGenerationsTerminator
from desdeo.problem import Problem
from desdeo.tools.patterns import Publisher


def rvea(
    *,
    problem: Problem,
    seed: int = 0,
    n_generations=100,
    reference_vector_options: ReferenceVectorOptions = None,
    forced_verbosity: int | None = None,
) -> tuple[Callable[[], EMOResult], Publisher]:
    """Implements the Reference Vector Guided Evolutionary Algorithm (RVEA), as well as its interactive version.

    References:
        R. Cheng, Y. Jin, M. Olhofer and B. Sendhoff, "A Reference Vector Guided Evolutionary Algorithm for Many-
        Objective Optimization," in IEEE Transactions on Evolutionary Computation, vol. 20, no. 5, pp. 773-791,
        Oct. 2016, doi: 10.1109/TEVC.2016.2519378.

        J. Hakanen, T. Chugh, K. Sindhya, Y. Jin, and K. Miettinen, “Connections of reference vectors and different
        types of preference information in interactive multiobjective evolutionary algorithms,” in 2016 IEEE Symposium
        Series on Computational Intelligence (SSCI), Athens, Greece: IEEE, Dec. 2016, pp. 1-8.


    Args:
        problem (Problem): The problem to be solved.
        seed (int, optional): The seed for the random number generator. Defaults to 0.
        n_generations (int, optional): The number of generations to run the algorithm. Defaults to 100.
        reference_vector_options (ReferenceVectorOptions, optional): The options for the reference vectors. Defaults to
            None. See the ReferenceVectorOptions class for the defaults. This option can be used to run an interactive
            version of the algorithm, using preferences provided by the user.
        forced_verbosity (int, optional): If not None, the verbosity of the algorithm is forced to this value. Defaults
            to None.

    Returns:
        tuple[Callable[[], EMOResult], Publisher]: A tuple containing the function to run the algorithm and the
            publisher object. The publisher object can be used to subscribe to the topics of the algorithm components,
            as well as to inject additional functionality such as archiving the results.
    """
    publisher = Publisher()
    evaluator = EMOEvaluator(
        problem=problem,
        publisher=publisher,
        verbosity=forced_verbosity if forced_verbosity is not None else 2,
    )

    selector = RVEASelector(
        problem=problem,
        publisher=publisher,
        reference_vector_options=reference_vector_options,
        verbosity=forced_verbosity if forced_verbosity is not None else 2,
    )

    # Note that the initial population size is equal to the number of reference vectors
    n_points = selector.reference_vectors.shape[0]

    generator = LHSGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=n_points,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    crossover = SimulatedBinaryCrossover(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    mutation = BoundedPolynomialMutation(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )

    terminator = MaxGenerationsTerminator(n_generations, publisher=publisher)

    components = [evaluator, generator, crossover, mutation, selector, terminator]
    [publisher.auto_subscribe(x) for x in components]
    [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]

    return (
        partial(
            template1,
            evaluator=evaluator,
            crossover=crossover,
            mutation=mutation,
            generator=generator,
            selection=selector,
            terminator=terminator,
        ),
        publisher,
    )


def nsga3(
    *,
    problem: Problem,
    seed: int = 0,
    n_generations: int = 100,
    reference_vector_options: ReferenceVectorOptions = None,
    forced_verbosity: int | None = None,
) -> tuple[Callable[[], EMOResult], Publisher]:
    """Implements the NSGA-III algorithm as well as its interactive version.

    References:
        K. Deb and H. Jain, “An Evolutionary Many-Objective Optimization Algorithm Using Reference-Point-Based
        Nondominated Sorting Approach, Part I: Solving Problems With Box Constraints,” IEEE Transactions on Evolutionary
        Computation, vol. 18, no. 4, pp. 577-601, Aug. 2014.

        J. Hakanen, T. Chugh, K. Sindhya, Y. Jin, and K. Miettinen, “Connections of reference vectors and different
        types of preference information in interactive multiobjective evolutionary algorithms,” in 2016 IEEE Symposium
        Series on Computational Intelligence (SSCI), Athens, Greece: IEEE, Dec. 2016, pp. 1-8.

    Args:
        problem (Problem): The problem to be solved.
        seed (int, optional): The seed for the random number generator. Defaults to 0.
        n_generations (int, optional): The number of generations to run the algorithm. Defaults to 100.
        reference_vector_options (ReferenceVectorOptions, optional): The options for the reference vectors. Defaults to
            None. See the ReferenceVectorOptions class for the defaults. This option can be used to run an interactive
            version of the algorithm, using preferences provided by the user.
        forced_verbosity (int, optional): If not None, the verbosity of the algorithm is forced to this value. Defaults
            to None.

    Returns:
        tuple[Callable[[], EMOResult], Publisher]: A tuple containing the function to run the algorithm and the
            publisher object. The publisher object can be used to subscribe to the topics of the algorithm components,
            as well as to inject additional functionality such as archiving the results.
    """
    publisher = Publisher()
    evaluator = EMOEvaluator(
        problem=problem,
        publisher=publisher,
        verbosity=forced_verbosity if forced_verbosity is not None else 2,
    )

    selector = NSGAIII_select(
        problem=problem,
        publisher=publisher,
        verbosity=forced_verbosity if forced_verbosity is not None else 2,
    )

    # Note that the initial population size is equal to the number of reference vectors
    n_points = selector.reference_vectors.shape[0]

    generator = LHSGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=n_points,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    crossover = SimulatedBinaryCrossover(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    mutation = BoundedPolynomialMutation(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )

    terminator = MaxGenerationsTerminator(
        n_generations,
        publisher=publisher,
    )

    components = [evaluator, generator, crossover, mutation, selector, terminator]
    [publisher.auto_subscribe(x) for x in components]
    [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]

    return (
        partial(
            template1,
            evaluator=evaluator,
            crossover=crossover,
            mutation=mutation,
            generator=generator,
            selection=selector,
            terminator=terminator,
        ),
        publisher,
    )
