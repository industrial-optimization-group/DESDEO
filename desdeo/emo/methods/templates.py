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
from desdeo.emo.operators.selection import ASFSelector, BaseSelector
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
    selection: ASFSelector,
    learning_operator: LearningModeOperator,
    terminator: BaseTerminator,
    repair: Callable[[pl.DataFrame], pl.DataFrame] = lambda x: x,
    n_darwin_per_cycle: int = 20,
    n_learning_per_cycle: int = 1,
) -> EMOResult:
    """Implements the XLEMOO loop alternating between Darwinian and Learning modes.

    Args:
        evaluator (EMOEvaluator): Evaluator for objective and target values.
        crossover (BaseCrossover): The crossover operator.
        mutation (BaseMutation): The mutation operator.
        generator (BaseGenerator): Initial population generator.
        selection (ASFSelector): ASF-based selection operator.
        learning_operator (LearningModeOperator): Operator that performs one learning step
            (rule extraction + instantiation) using the archive.
        terminator (BaseTerminator): Termination operator. Its `check()` advances the
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
    solutions, outputs = generator.do()

    while not terminator.check():
        stop = False

        for _ in range(n_darwin_per_cycle):
            offspring = crossover.do(population=solutions)
            offspring = mutation.do(offspring, solutions)
            offspring = repair(offspring)
            offspring_outputs = evaluator.evaluate(offspring)
            solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))
            if terminator.check():
                stop = True
                break
        if stop:
            break

        for _ in range(n_learning_per_cycle):
            solutions, outputs = learning_operator.do()
            # Re-publish the new population through the pub/sub flow so the archive sees it.
            outputs = evaluator.evaluate(solutions)
            empty_solutions = pl.DataFrame(schema=solutions.schema)
            empty_outputs = pl.DataFrame(schema=outputs.schema)
            solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(empty_solutions, empty_outputs))
            if terminator.check():
                stop = True
                break
        if stop:
            break

    return EMOResult(optimal_variables=solutions, optimal_outputs=outputs)
