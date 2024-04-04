"""Implements and evaluator based on sympy expressions."""

from desdeo.problem.json_parser import MathParser, FormatEnum
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
        self.constant_expressions = (
            [(const.symbol, sp.sympify(const.value, evaluate=False)) for const in problem.constants]
            if problem.constants is not None
            else None
        )

        self.extra_expressions = (
            [(extra.symbol, sp.sympify(extra.func, evaluate=False)) for extra in problem.extra_funcs]
            if problem.extra_funcs is not None
            else None
        )

        self.objective_expressions = [(obj.symbol, sp.sympify(obj.func, evaluate=False)) for obj in problem.objectives]

        self.constraint_expressions = (
            [(con.symbol, sp.sympify(con.func, evaluate=False)) for con in problem.constraints]
            if problem.constraints is not None
            else None
        )

        self.scalarization_expressions = (
            [(scal.symbol, sp.sympify(scal.func, evaluate=False)) for scal in problem.scalarization_funcs]
            if problem.scalarization_funcs is not None
            else None
        )
