"""This module contains the basic functional implementations for the EMO methods.

This can be used as a template for the implementation of the EMO methods.
"""

from desdeo.emo.operators.crossover import BaseCrossover
from desdeo.emo.operators.evaluator import BaseEvaluator
from desdeo.emo.operators.generator import BaseGenerator
from desdeo.emo.operators.mutation import BaseMutation
from desdeo.emo.operators.selection import BaseSelector
from desdeo.emo.operators.termination import BaseTerminator
from desdeo.problem import Problem


def baseEA1(
    problem: Problem,
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

    return (
        (solutions, targets),
        termination.state(),
        crossover.state(),
        mutation.state(),
        selection.state(),
    )
