"""This module contains the basic functional implementations for the EMO methods.

This can be used as a template for the implementation of the EMO methods.
"""

from collections.abc import Callable

import polars as pl

from desdeo.emo.operators.crossover import BaseCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import BaseGenerator
from desdeo.emo.operators.learning_mode import LearningModeOperator
from desdeo.emo.operators.mutation import BaseMutation
from desdeo.emo.operators.scalar_selection import BaseScalarSelector
from desdeo.emo.operators.selection import BaseSelector
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
            identity function, meaning no repair is done. See :py:func:`desdeo.tools.utils.repair` as an example of a
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
    selection: BaseSelector,
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
        selection (BaseSelector): The selection operator.
        mate_selection (BaseScalarSelector): The mating selection operator, which selects parents for mating.
            This is typically a scalar selector that selects parents based on their fitness.
        terminator (BaseTerminator): The termination operator.
        repair (Callable, optional): A function that repairs the offspring if they go out of bounds. Defaults to an
            identity function, meaning no repair is done. See :py:func:`desdeo.tools.utils.repair` as an example of a
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
            :class:`~desdeo.emo.operators.scalar_selection.ElitistSelection`).
        learning_operator (LearningModeOperator): Operator that performs one learning step
            (rule extraction + instantiation) using the archive. Its :meth:`do` returns
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
