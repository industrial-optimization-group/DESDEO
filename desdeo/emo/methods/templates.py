"""This module contains the basic functional implementations for the EMO methods.

This can be used as a template for the implementation of the EMO methods.
"""

from collections.abc import Callable

import numpy as np
import polars as pl

from desdeo.emo.operators.crossover import BaseCrossover, DifferentialEvolutionCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import BaseGenerator
from desdeo.emo.operators.learning_mode import LearningModeOperator
from desdeo.emo.operators.mutation import BaseMutation
from desdeo.emo.operators.scalar_selection import BaseScalarSelector
from desdeo.emo.operators.selection import BaseSelector, MOEADSelector, _FitnessPublishingSelector
from desdeo.emo.operators.termination import BaseTerminator
from desdeo.tools.generics import EMOResult


def template1(
    evaluator: EMOEvaluator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    generator: BaseGenerator,
    selection: BaseSelector,
    terminator: BaseTerminator,
    repair: Callable[[pl.DataFrame], pl.DataFrame] = lambda x: x,  # Default to identity function if no repair is needed
) -> EMOResult:
    """Implements a template that many EMO methods, such as RVEA and NSGA-III, follow.

    Args:
        evaluator (EMOEvaluator): A class that evaluates the solutions and provides the objective vectors, constraint
            vectors, and targets.
        crossover (BaseCrossover): The crossover operator.
        mutation (BaseMutation): The mutation operator.
        generator (BaseGenerator): A class that generates the initial population.
        selection (BaseSelector): The selection operator.
        terminator (BaseTerminator): The termination operator.
        repair (Callable, optional): A function that repairs the offspring if they go out of bounds. Defaults to an
            identity function, meaning no repair is done. See [desdeo.tools.utils.repair][] as an example of a
            repair function.

    Returns:
        EMOResult: The final population and their objective vectors, constraint vectors, and targets
    """
    solutions, outputs = generator.do()

    while not terminator.check():
        offspring = crossover.do(population=solutions)
        offspring = mutation.do(offspring, solutions)
        # Repair offspring if they go out of bounds
        offspring = repair(offspring)
        offspring_outputs = evaluator.evaluate(offspring)
        solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))

    return EMOResult(optimal_variables=solutions, optimal_outputs=outputs)


def template2(
    evaluator: EMOEvaluator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    generator: BaseGenerator,
    selection: _FitnessPublishingSelector,
    mate_selection: BaseScalarSelector,
    terminator: BaseTerminator,
    repair: Callable[[pl.DataFrame], pl.DataFrame] = lambda x: x,  # Default to identity function if no repair is needed
) -> EMOResult:
    """Implements a template that many EMO methods, such as IBEA, follow.

    Args:
        evaluator (EMOEvaluator): A class that evaluates the solutions and provides the objective vectors, constraint
            vectors, and targets.
        crossover (BaseCrossover): The crossover operator.
        mutation (BaseMutation): The mutation operator.
        generator (BaseGenerator): A class that generates the initial population.
        selection (_FitnessPublishingSelector): The selection operator. It publishes the fitness that
            `mate_selection` picks parents by.
        mate_selection (BaseScalarSelector): The mating selection operator, which selects parents for mating.
            This is typically a scalar selector that selects parents based on their fitness.
        terminator (BaseTerminator): The termination operator.
        repair (Callable, optional): A function that repairs the offspring if they go out of bounds. Defaults to an
            identity function, meaning no repair is done. See [desdeo.tools.utils.repair][] as an example of a
            repair function.

    Returns:
        EMOResult: The final population and their objective vectors, constraint vectors, and targets
    """
    solutions, outputs = generator.do()
    # This is just a hack to make all selection operators work (they require offsprings to be passed separately rn)
    offspring = pl.DataFrame(
        schema=solutions.schema,
    )
    offspring_outputs = pl.DataFrame(
        schema=outputs.schema,
    )

    while True:
        solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))
        if terminator.check():
            # Weird way to do looping, but IBEA does environmental selection before the loop check, and...
            # does mating afterwards.
            break
        parents, _ = mate_selection.do((solutions, outputs))
        offspring = crossover.do(population=parents)
        offspring = mutation.do(offspring, solutions)
        # Repair offspring if they go out of bounds
        offspring = repair(offspring)
        offspring_outputs = evaluator.evaluate(offspring)

    return EMOResult(optimal_variables=solutions, optimal_outputs=outputs)


def template3(
    evaluator: EMOEvaluator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    generator: BaseGenerator,
    selection: BaseSelector,
    terminator: BaseTerminator,
    seed: int,
    repair: Callable[[pl.DataFrame], pl.DataFrame] = lambda x: x,  # Default to identity function if no repair is needed
) -> EMOResult:
    """Implements a template that many steady state EMO methods such as SMS-EMOA follow.

    The algorithm follows the one described in Beume et al. (2007).

    Beume, N., Naujoks, B., & Emmerich, M. (2007). SMS-EMOA: Multiobjective selection based on dominated hypervolume.
    European Journal of Operational Research, 181(3), 1653-1669. https://doi.org/10.1016/j.ejor.2006.08.008


    Args:
        evaluator (EMOEvaluator): A class that evaluates the solutions and provides the objective vectors, constraint
            vectors, and targets.
        crossover (BaseCrossover): The crossover operator.
        mutation (BaseMutation): The mutation operator.
        generator (BaseGenerator): A class that generates the initial population.
        selection (BaseSelector): The selection operator.
        terminator (BaseTerminator): The termination operator.
        seed (int): The random seed for reproducibility.
        repair (Callable, optional): A function that repairs the offspring if they go out of bounds. Defaults to an
            identity function, meaning no repair is done. See [desdeo.tools.utils.repair][] as an example of a
            repair function.

    Returns:
        EMOResult: The final population and their objective vectors, constraint vectors, and targets
    """
    rng = np.random.default_rng(seed)
    solutions, outputs = generator.do()  # Algorithm 1 line 1

    while not terminator.check():
        # Generate one offspring at a time
        # choose two random parents from the current population
        parents_idx = rng.choice(solutions.height, size=2, replace=False).tolist()
        offsprings = crossover.do(population=solutions, to_mate=parents_idx)  # Algorithm 1 line 4
        offsprings = mutation.do(offsprings, solutions)  # Algorithm 1 line 4
        # Repair offspring if they go out of bounds
        offsprings = repair(offsprings)
        # The crossover generates two offsprings, but we only want to keep one of them,
        # so we randomly choose one of the two (i think just always choosing the first one is not fine)
        offspring_idx = rng.choice(offsprings.height, size=1, replace=False).tolist()
        offspring = offsprings[offspring_idx, :]
        offspring_outputs = evaluator.evaluate(offspring)
        solutions, outputs = selection.do(
            parents=(solutions, outputs), offsprings=(offspring, offspring_outputs)
        )  # Algorithm 1 line 5

    return EMOResult(optimal_variables=solutions, optimal_outputs=outputs)


def template_xlemoo(
    evaluator: EMOEvaluator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    generator: BaseGenerator,
    selection: BaseScalarSelector,
    learning_operator: LearningModeOperator,
    terminator: BaseTerminator,
    repair: Callable[[pl.DataFrame], pl.DataFrame] = lambda x: x,
    n_darwin_per_cycle: int = 20,
    n_learning_per_cycle: int = 1,
) -> EMOResult:
    """Implements the XLEMOO loop alternating between Darwinian and Learning modes.

    The loop interleaves ``n_darwin_per_cycle`` Darwinian iterations with
    ``n_learning_per_cycle`` Learning iterations. Each iteration counts as one
    generation against the terminator, so the cycle structure is just a phase
    selector for what happens inside that generation.

    Args:
        evaluator (EMOEvaluator): Evaluator for objective and target values.
        crossover (BaseCrossover): The crossover operator.
        mutation (BaseMutation): The mutation operator.
        generator (BaseGenerator): Initial population generator.
        selection (BaseScalarSelector): Scalar selector that ranks the combined parent
            and offspring population by a single fitness column (e.g.
            [ElitistSelection][desdeo.emo.operators.scalar_selection.ElitistSelection]).
        learning_operator (LearningModeOperator): Operator that performs one learning step
            (rule extraction + instantiation) using the archive. Its `do()` returns
            instantiated decision vectors (or ``None`` when no rules can be extracted).
        terminator (BaseTerminator): Termination operator. Its ``check()`` advances the
            generation counter and notifies subscribers (e.g. the Archive).
        repair (Callable, optional): Function repairing offspring back into bounds. Defaults
            to identity.
        n_darwin_per_cycle (int, optional): Number of Darwinian iterations per cycle.
            Defaults to 20.
        n_learning_per_cycle (int, optional): Number of Learning iterations per cycle. Set
            to 0 to disable Learning mode entirely. Defaults to 1.

    Returns:
        EMOResult: The final population and its objective/target values.
    """
    if n_darwin_per_cycle == 0 and n_learning_per_cycle == 0:
        raise ValueError("At least one of n_darwin_per_cycle and n_learning_per_cycle must be > 0.")

    cycle_len = n_darwin_per_cycle + n_learning_per_cycle
    solutions, outputs = generator.do()
    gen_in_cycle = 0

    while not terminator.check():
        if gen_in_cycle < n_darwin_per_cycle:
            offspring = crossover.do(population=solutions)
            offspring = mutation.do(offspring, solutions)
            offspring = repair(offspring)
            offspring_outputs = evaluator.evaluate(offspring)
            combined_decvars = solutions.vstack(offspring)
            combined_outputs = outputs.vstack(offspring_outputs)
            solutions, outputs = selection.do((combined_decvars, combined_outputs))
        else:
            instantiated = learning_operator.do()
            if instantiated is not None:
                instantiated_outputs = evaluator.evaluate(instantiated)
                combined_decvars = solutions.vstack(instantiated)
                combined_outputs = outputs.vstack(instantiated_outputs)
                solutions, outputs = selection.do((combined_decvars, combined_outputs))
            # else: no usable rules this round; keep the current population unchanged
        gen_in_cycle = (gen_in_cycle + 1) % cycle_len

    return EMOResult(optimal_variables=solutions, optimal_outputs=outputs)


def template_moead(
    evaluator: EMOEvaluator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    generator: BaseGenerator,
    selection: MOEADSelector,
    terminator: BaseTerminator,
    seed: int,
    repair: Callable[[pl.DataFrame], pl.DataFrame] = lambda x: x,  # Default to identity function if no repair is needed
) -> EMOResult:
    """Implements the main loop of MOEA/D and MOEA/D-DE.

    Each generation visits the subproblems in order. For subproblem `i` it draws a mating pool, makes
    one offspring from parents in that pool, evaluates it, and lets it replace solutions in the pool
    straight away, so the next subproblem already mates with the updated population. A generation
    therefore spends exactly as many evaluations as there are subproblems, one at a time.

    How the parents are drawn depends on the crossover. For
    [DifferentialEvolutionCrossover][desdeo.emo.operators.crossover.DifferentialEvolutionCrossover]
    the current solution `x_i` is the target and the donors come from the pool (MOEA/D-DE, Step 2.2);
    set its `base_vector` to "target" to get MOEA/D-DE's `x_i + F * (x_r2 - x_r3)`. Any other
    crossover gets two distinct parents drawn from the pool (MOEA/D, Step 2.1), and one of the
    children it returns is kept at random.

    The final population, one solution per subproblem, is returned. Neither paper's continuous
    experiments keep the external population of nondominated solutions (Zhang and Li 2007,
    Section V-C); use the template's archive for that.

    References:
        Zhang, Q., & Li, H. (2007). MOEA/D: A multiobjective evolutionary algorithm based on
            decomposition. IEEE Transactions on Evolutionary Computation, 11(6), 712-731.
            https://doi.org/10.1109/TEVC.2007.892759

        Li, H., & Zhang, Q. (2009). Multiobjective optimization problems with complicated Pareto
            sets, MOEA/D and NSGA-II. IEEE Transactions on Evolutionary Computation, 13(2), 284-302.
            https://doi.org/10.1109/TEVC.2008.925798

    Args:
        evaluator (EMOEvaluator): A class that evaluates the solutions and provides the objective vectors, constraint
            vectors, and targets.
        crossover (BaseCrossover): The crossover operator.
        mutation (BaseMutation): The mutation operator.
        generator (BaseGenerator): A class that generates the initial population, one solution per subproblem.
        selection (MOEADSelector): The MOEA/D selector, which holds the weight vectors, the neighbourhoods and the
            ideal point.
        terminator (BaseTerminator): The termination operator, checked once per generation.
        seed (int): The random seed for drawing parents from the mating pool.
        repair (Callable, optional): A function that repairs the offspring if they go out of bounds. Defaults to an
            identity function, meaning no repair is done. See [desdeo.tools.utils.repair][] as an example of a
            repair function.

    Returns:
        EMOResult: The final population and their objective vectors, constraint vectors, and targets
    """
    rng = np.random.default_rng(seed)
    target_aligned = isinstance(crossover, DifferentialEvolutionCrossover)

    solutions, outputs = generator.do()  # 2007 Step 1.3, 2009 Step 1.2
    # The neighbourhoods (2007 Step 1.2, 2009 Step 1.1) were built with the selector; this sets z.
    solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(solutions.clear(), outputs.clear()))

    while not terminator.check():
        for i in range(selection.number_of_subproblems):  # Step 2
            pool = selection.mating_pool(i)  # 2009 Step 2.1
            if target_aligned:
                # 2009 Step 2.2: r1 = i, and r2, r3 from the pool.
                position = int(np.flatnonzero(pool == i)[0])
                offspring = crossover.do(population=solutions[pool.tolist()], to_mate=[position])
            else:
                # 2007 Step 2.1: two parents from B(i), and one offspring.
                parents = rng.choice(pool, size=2, replace=False).tolist()
                offspring = crossover.do(population=solutions, to_mate=parents)
                offspring = offspring[[int(rng.integers(offspring.height))]]
            offspring = mutation.do(offspring, solutions)
            offspring = repair(offspring)  # 2009 Step 2.3
            offspring_outputs = evaluator.evaluate(offspring)
            # 2007 Steps 2.3-2.4, 2009 Steps 2.4-2.5
            solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))
        selection.notify()

    return EMOResult(optimal_variables=solutions, optimal_outputs=outputs)
