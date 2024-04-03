"""Implements and evaluator based on sympy expressions."""

from desdeo.problem.math_parser import MathParser, FormatEnum
from desdeo.problem.schema import Problem

import sympy as sp


class SympyEvaluatorError(Exception):
    """Raised when an error withing the SympyEvaluator class is encountered."""


class SympyEvaluator:
    """Defines an evaluator that can be used to evaluate instances of Problem utilizing sympy."""

    def __init__(self, problem: Problem):
        """Initializes the evaluator.

        Args:
            problem (Problem): the problem to be evaluated.
        """
        self.variable_symbols = [var.symbol for var in problem.variables]

        self.parse = MathParser(to_format=FormatEnum.sympy)

        self.extra_exprs = (
            [self.parse(extra.func) for extra in problem.extra_funcs] if problem.extra_funcs is not None else None
        )

        self.constraint_expr = (
            [self.parse(const.func) for const in problem.constraints] if problem.constraints is not None else None
        )

        self.objective_expr = [self.parse(obj.func) for obj in problem.objectives]

        self.scalarization_expr = (
            [self.parse(scal.func) for scal in problem.scalarization_funcs]
            if problem.scalarization_funcs is not None
            else None
        )
