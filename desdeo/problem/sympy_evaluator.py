"""Implements and evaluator based on sympy expressions."""

from copy import deepcopy

import sympy as sp

from desdeo.problem.evaluator import variable_dimension_enumerate
from desdeo.problem.json_parser import FormatEnum, MathParser
from desdeo.problem.schema import Problem

SUPPORTED_VAR_DIMENSIONS = ["scalar"]


class SympyEvaluatorError(Exception):
    """Raised when an exception with a Sympy evaluator is encountered."""


class SympyEvaluator:
    """Defines an evaluator that can be used to evaluate instances of Problem utilizing sympy."""

    def __init__(self, problem: Problem):
        """Initializes the evaluator.

        Args:
            problem (Problem): the problem to be evaluated.
        """
        if variable_dimension_enumerate(problem) not in SUPPORTED_VAR_DIMENSIONS:
            msg = "SymPy evaluator does not yet support tensors."
            raise SympyEvaluatorError(msg)

        # Collect all the symbols and expressions in the problem
        parser = MathParser(to_format=FormatEnum.sympy)

        self.variable_symbols = [var.symbol for var in problem.variables]
        self.constant_expressions = (
            {const.symbol: parser.parse(const.value) for const in problem.constants}
            if problem.constants is not None
            else None
        )

        self.extra_expressions = (
            {extra.symbol: parser.parse(extra.func) for extra in problem.extra_funcs}
            if problem.extra_funcs is not None
            else None
        )

        self.objective_expressions = {obj.symbol: parser.parse(obj.func) for obj in problem.objectives}

        self.constraint_expressions = (
            {con.symbol: parser.parse(con.func) for con in problem.constraints}
            if problem.constraints is not None
            else None
        )

        self.scalarization_expressions = (
            {scal.symbol: parser.parse(scal.func) for scal in problem.scalarization_funcs}
            if problem.scalarization_funcs is not None
            else None
        )

        # replace symbols and create lambda functions ready to be called
        # replace constants in extra functions, if they exist
        if self.extra_expressions is not None:
            _extra_expressions = (
                {
                    k: self.extra_expressions[k].subs(self.constant_expressions, evaluate=False)
                    for k in self.extra_expressions
                }
                if self.constant_expressions is not None
                else deepcopy(self.extra_expressions)
            )
        else:
            _extra_expressions = None

        # replace constants in objective functions, if constants have been defined
        _objective_expressions = (
            {
                k: self.objective_expressions[k].subs(self.constant_expressions, evaluate=False)
                for k in self.objective_expressions
            }
            if self.constant_expressions is not None
            else deepcopy(self.objective_expressions)
        )

        # replace extra functions in objective functions, if extra functions have been defined
        _objective_expressions = (
            (
                {
                    k: _objective_expressions[k].subs(self.extra_expressions, evaluate=False)
                    for k in _objective_expressions
                }
            )
            if self.extra_expressions is not None
            else _objective_expressions
        )

        # always minimized objective expressions
        _objective_expressions_min = {
            f"{obj.symbol}_min": -_objective_expressions[obj.symbol]
            if obj.maximize
            else _objective_expressions[obj.symbol]
            for obj in problem.objectives
        }

        # replace stuff in the constraint expressions if any are defined
        if self.constraint_expressions is not None:
            # replace constants
            _constraint_expressions = (
                {
                    k: self.constraint_expressions[k].subs(self.constant_expressions, evaluate=False)
                    for k in self.constraint_expressions
                }
                if self.constant_expressions is not None
                else deepcopy(self.constraint_expressions)
            )

            # replace extra functions
            _constraint_expressions = (
                {
                    k: _constraint_expressions[k].subs(_extra_expressions, evaluate=False)
                    for k in _constraint_expressions
                }
                if _extra_expressions is not None
                else _constraint_expressions
            )

            # replace objective functions
            _constraint_expressions = {
                k: _constraint_expressions[k].subs(_objective_expressions, evaluate=False)
                for k in _constraint_expressions
            }
            _constraint_expressions = {
                k: _constraint_expressions[k].subs(_objective_expressions_min, evaluate=False)
                for k in _constraint_expressions
            }

        else:
            _constraint_expressions = None

        # replace stuff in scalarization expressions if any are defined
        if self.scalarization_expressions is not None:
            # replace constants
            _scalarization_expressions = (
                {
                    k: self.scalarization_expressions[k].subs(self.constant_expressions, evaluate=False)
                    for k in self.scalarization_expressions
                }
                if self.constant_expressions is not None
                else deepcopy(self.scalarization_expressions)
            )

            # replace extra functions
            _scalarization_expressions = (
                {
                    k: _scalarization_expressions[k].subs(_extra_expressions, evaluate=False)
                    for k in _scalarization_expressions
                }
                if _extra_expressions is not None
                else _scalarization_expressions
            )

            # replace constraints
            _scalarization_expressions = (
                {
                    k: _scalarization_expressions[k].subs(_constraint_expressions, evaluate=False)
                    for k in _scalarization_expressions
                }
                if _constraint_expressions is not None
                else _scalarization_expressions
            )

            # replace objectives
            _scalarization_expressions = {
                k: _scalarization_expressions[k].subs(_objective_expressions, evaluate=False)
                for k in _scalarization_expressions
            }

            _scalarization_expressions = {
                k: _scalarization_expressions[k].subs(_objective_expressions_min, evaluate=False)
                for k in _scalarization_expressions
            }

        else:
            _scalarization_expressions = None

        # initialize callable lambdas
        self.lambda_exprs = {
            _k: _v
            for _d in [
                {k: sp.lambdify(self.variable_symbols, d[k]) for k in d}
                for d in [
                    _extra_expressions,
                    _objective_expressions,
                    _objective_expressions_min,
                    _constraint_expressions,
                    _scalarization_expressions,
                ]
                if d is not None
            ]
            for _k, _v in _d.items()
        }

        self.problem = problem
        self.parser = parser

    def evaluate(self, xs: dict[str, float | int | bool]) -> dict[str, float | int | bool]:
        """Evaluate the the whole problem with a given decision variable dict.

        Args:
            xs (dict[str, float  |  int  |  bool]): a dict with keys representing decision variable
                symbols and values with the decision variable value.

        Returns:
            dict[str, float | int | bool]: a dict with keys corresponding to each symbol
                defined for the problem being evaluated and the corresponding expression's
                value.
        """
        return {k: self.lambda_exprs[k](**xs) for k in self.lambda_exprs} | xs

    def evaluate_target(self, xs: dict[str, float | int | bool], target: str) -> float:
        """Evaluates only the specified target with given decision variables.

        Args:
            xs (dict[str, float  |  int  |  bool]): a dict with keys representing decision variable
                symbols and values with the decision variable value.
            target (str): the symbol of the function expressions to be evaluated.

        Returns:
            float: the value of the target once evaluated.
        """
        return self.lambda_exprs[target](**xs)

    def evaluate_constraints(self, xs: dict[str, float | int | bool]) -> dict[str, float | int | bool]:
        """Evaluates the constraints of the problem with given decision variables.

        Args:
            xs (dict[str, float  |  int  |  bool]): a dict with keys representing decision variable
                symbols and values with the decision variable value.

        Returns:
            dict[str, float | int | bool]: a dict with keys being the constraints symbols
                and values being the value of the corresponding constraint.
        """
        return {k: self.lambda_exprs[k](**xs) for k in [constr.symbol for constr in self.problem.constraints]}
