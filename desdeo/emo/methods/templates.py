"""This module contains the basic functional implementations for the EMO methods.

This can be used as a template for the implementation of the EMO methods.
"""

from collections.abc import Callable

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from desdeo.emo.operators.crossover import BaseCrossover
from desdeo.emo.operators.evaluator import EMOEvaluator
from desdeo.emo.operators.generator import BaseGenerator
from desdeo.emo.operators.mutation import BaseMutation
from desdeo.emo.operators.scalar_selection import BaseScalarSelector
from desdeo.emo.operators.selection import BaseSelector
from desdeo.emo.operators.termination import BaseTerminator


class EMOResult(BaseModel):
    solutions: pl.DataFrame = Field(description="The decision vectors of the final population.")
    """The decision vectors of the final population."""
    outputs: pl.DataFrame = Field(
        description="The objective vectors, constraint vectors, and targets of the final population."
    )
    """The objective vectors, constraint vectors, and targets of the final population."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


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

    return EMOResult(solutions=solutions, outputs=outputs)


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

    return EMOResult(solutions=solutions, outputs=outputs)
