"""This module contains the basic functional implementations for the EMO methods.

This can be used as a template for the implementation of the EMO methods.
"""

import numpy as np
import polars as pl
from pydantic import BaseModel, ConfigDict

from desdeo.emo.operators.crossover import BaseCrossover
from desdeo.emo.operators.evaluator import BaseEvaluator
from desdeo.emo.operators.generator import BaseGenerator
from desdeo.emo.operators.mutation import BaseMutation
from desdeo.emo.operators.selection import BaseSelector
from desdeo.emo.operators.termination import BaseTerminator


class EMOResult(BaseModel):
    solutions: pl.DataFrame
    outputs: pl.DataFrame

    model_config = ConfigDict(arbitrary_types_allowed=True)


def baseEA1(
    evaluator: BaseEvaluator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    generator: BaseGenerator,
    selection: BaseSelector,
    termination: BaseTerminator,
):
    solutions, outputs = generator.do()

    while not termination.check():
        offspring = crossover.do(population=solutions)
        offspring = mutation.do(offspring, solutions)
        offspring_outputs = evaluator.evaluate(offspring)
        solutions, outputs = selection.do(parents=(solutions, outputs), offsprings=(offspring, offspring_outputs))

    return EMOResult(solutions=solutions, outputs=outputs)
