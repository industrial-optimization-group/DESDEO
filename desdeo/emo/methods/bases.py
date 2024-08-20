"""This module contains the basic functional implementations for the EMO methods.

This can be used as a template for the implementation of the EMO methods.
"""

from pydantic import BaseModel, Field
import numpy as np

from desdeo.emo.operators.crossover import BaseCrossover
from desdeo.emo.operators.evaluator import BaseEvaluator
from desdeo.emo.operators.generator import BaseGenerator
from desdeo.emo.operators.mutation import BaseMutation
from desdeo.emo.operators.selection import BaseSelector
from desdeo.emo.operators.termination import BaseTerminator


class EMOResult(BaseModel):
    solutions: np.ndarray
    objectives: np.ndarray


def baseEA1(
    evaluator: BaseEvaluator,
    crossover: BaseCrossover,
    mutation: BaseMutation,
    generator: BaseGenerator,
    selection: BaseSelector,
    termination: BaseTerminator,
):
    solutions, objectives, targets, cons_violations = generator.do()

    while not termination.check():
        offspring = crossover.do(population=(solutions, targets, cons_violations))
        offspring = mutation.do(offspring, solutions)
        offspring_objs, offspring_targets, offspring_constraints = evaluator.evaluate(offspring)
        solutions, targets, cons_violations = selection.do(
            (solutions, targets, cons_violations),
            (offspring, offspring_targets, offspring_constraints),
        )

    return EMOResult(solutions=solutions, objectives=objectives)
