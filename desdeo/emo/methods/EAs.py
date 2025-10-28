"""[Deprecated] Implements common evolutionary algorithms for multi-objective optimization.

Use desdeo.emo.options.algorithms instead.
"""

from collections.abc import Callable
from functools import partial
from warnings import warn

import numpy as np

from desdeo.emo.methods.templates import EMOResult, template1, template2
from desdeo.emo.operators.crossover import SimulatedBinaryCrossover, UniformMixedIntegerCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import LHSGenerator, RandomMixedIntegerGenerator
from desdeo.emo.operators.mutation import BoundedPolynomialMutation, MixedIntegerRandomMutation
from desdeo.emo.operators.scalar_selection import TournamentSelection
from desdeo.emo.operators.selection import IBEASelector, NSGA3Selector, ReferenceVectorOptions, RVEASelector
from desdeo.emo.operators.termination import MaxEvaluationsTerminator, MaxGenerationsTerminator
from desdeo.problem import Problem
from desdeo.tools.indicators_binary import self_epsilon
from desdeo.tools.patterns import Publisher

warn(
    "desdeo.emo.methods.EAs is deprecated and will be removed in future versions. "
    "Please use desdeo.emo.options.algorithms instead.",
    category=DeprecationWarning,
    stacklevel=1,
)


def rvea(
    *,
    problem: Problem,
    seed: int = 0,
    n_generations=100,
    max_evaluations: int | None = None,
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
        max_evaluations (int, optional): The maximum number of evaluations to run the algorithm. If None, the algorithm
            will run for n_generations. Defaults to None. If both n_generations and max_evaluations are provided, the
            algorithm will run until max_evaluations is reached.
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

    if max_evaluations is not None:
        terminator = MaxEvaluationsTerminator(max_evaluations, publisher=publisher)
    else:
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
    max_evaluations: int | None = None,
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
        max_evaluations (int, optional): The maximum number of evaluations to run the algorithm. If None, the algorithm
            will run for n_generations. Defaults to None. If both n_generations and max_evaluations are provided, the
            algorithm will run until max_evaluations is reached.
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

    selector = NSGA3Selector(
        problem=problem,
        publisher=publisher,
        verbosity=forced_verbosity if forced_verbosity is not None else 2,
        reference_vector_options=reference_vector_options,
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

    if max_evaluations is not None:
        terminator = MaxEvaluationsTerminator(max_evaluations, publisher=publisher)
    else:
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


def ibea(
    *,
    problem: Problem,
    population_size: int = 100,
    n_generations: int = 100,
    max_evaluations: int | None = None,
    kappa: float = 0.05,
    binary_indicator: Callable[[np.ndarray], np.ndarray] = self_epsilon,
    seed: int = 0,
    forced_verbosity: int | None = None,
) -> tuple[Callable[[], EMOResult], Publisher]:
    """Implements the Indicator-Based Evolutionary Algorithm (IBEA).

    References:
        Zitzler, E., Künzli, S. (2004). Indicator-Based Selection in Multiobjective Search. In: Yao, X., et al.
        Parallel Problem Solving from Nature - PPSN VIII. PPSN 2004. Lecture Notes in Computer Science, vol 3242.
        Springer, Berlin, Heidelberg. https://doi.org/10.1007/978-3-540-30217-9_84

    Args:
        problem (Problem): The problem to be solved.
        population_size (int, optional): The size of the population. Defaults to 100.
        n_generations (int, optional): The number of generations to run the algorithm. Defaults to 100.
        max_evaluations (int | None, optional): The maximum number of evaluations to run the algorithm. If None, the
            algorithm will run for n_generations. Defaults to None. If both n_generations and max_evaluations are
            provided, the algorithm will run until max_evaluations is reached.
        kappa (float, optional): The kappa value for the IBEA selection. Defaults to 0.05.
        binary_indicator (Callable[[np.ndarray], np.ndarray], optional): A binary indicator function that takes the
            target values and returns a binary indicator for each individual. Defaults to self_epsilon with uses
            binary adaptive epsilon indicator.
        seed (int, optional): The seed for the random number generator. Defaults to 0.
        forced_verbosity (int | None, optional): If not None, the verbosity of the algorithm is forced to this value.
            Defaults to None.

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
    selector = IBEASelector(
        problem=problem,
        verbosity=forced_verbosity if forced_verbosity is not None else 2,
        publisher=publisher,
        population_size=population_size,
        kappa=kappa,
        binary_indicator=binary_indicator,
    )
    generator = LHSGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=population_size,
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
    if max_evaluations is not None:
        terminator = MaxEvaluationsTerminator(max_evaluations, publisher=publisher)
    else:
        terminator = MaxGenerationsTerminator(
            n_generations,
            publisher=publisher,
        )

    scalar_selector = TournamentSelection(publisher=publisher, verbosity=0, winner_size=population_size, seed=seed)

    components = [
        evaluator,
        generator,
        crossover,
        mutation,
        selector,
        terminator,
        scalar_selector,
    ]
    [publisher.auto_subscribe(x) for x in components]
    [publisher.register_topics(x.provided_topics[x.verbosity], x.__class__.__name__) for x in components]
    return (
        partial(
            template2,
            evaluator=evaluator,
            crossover=crossover,
            mutation=mutation,
            generator=generator,
            selection=selector,
            terminator=terminator,
            mate_selection=scalar_selector,
        ),
        publisher,
    )


def nsga3_mixed_integer(
    *,
    problem: Problem,
    seed: int = 0,
    n_generations: int = 100,
    max_evaluations: int | None = None,
    reference_vector_options: ReferenceVectorOptions = None,
    forced_verbosity: int | None = None,
) -> tuple[Callable[[], EMOResult], Publisher]:
    """Implements the NSGA-III algorithm as well as its interactive version for mixed-integer problems.

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
        max_evaluations (int, optional): The maximum number of evaluations to run the algorithm. If None, the algorithm
            will run for n_generations. Defaults to None. If both n_generations and max_evaluations are provided, the
            algorithm will run until max_evaluations is reached.
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

    selector = NSGA3Selector(
        problem=problem,
        publisher=publisher,
        verbosity=forced_verbosity if forced_verbosity is not None else 2,
        reference_vector_options=reference_vector_options,
    )

    # Note that the initial population size is equal to the number of reference vectors
    n_points = selector.reference_vectors.shape[0]

    generator = RandomMixedIntegerGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=n_points,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    crossover = UniformMixedIntegerCrossover(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    mutation = MixedIntegerRandomMutation(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )

    if max_evaluations is not None:
        terminator = MaxEvaluationsTerminator(max_evaluations, publisher=publisher)
    else:
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


def rvea_mixed_integer(
    *,
    problem: Problem,
    seed: int = 0,
    n_generations=100,
    max_evaluations: int | None = None,
    reference_vector_options: ReferenceVectorOptions = None,
    forced_verbosity: int | None = None,
) -> tuple[Callable[[], EMOResult], Publisher]:
    """Implements the mixed-integer variant of RVEA, as well as its interactive version.

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
        max_evaluations (int, optional): The maximum number of evaluations to run the algorithm. If None, the algorithm
            will run for n_generations. Defaults to None. If both n_generations and max_evaluations are provided, the
            algorithm will run until max_evaluations is reached.
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

    generator = RandomMixedIntegerGenerator(
        problem=problem,
        evaluator=evaluator,
        publisher=publisher,
        n_points=n_points,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    crossover = UniformMixedIntegerCrossover(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )
    mutation = MixedIntegerRandomMutation(
        problem=problem,
        publisher=publisher,
        seed=seed,
        verbosity=forced_verbosity if forced_verbosity is not None else 1,
    )

    if max_evaluations is not None:
        terminator = MaxEvaluationsTerminator(max_evaluations, publisher=publisher)
    else:
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
