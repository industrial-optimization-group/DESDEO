"""Implements and evaluator based on sympy expressions."""

import sympy as sp

from desdeo.problem.evaluator import variable_dimension_enumerate
from desdeo.problem.json_parser import FormatEnum, MathParser
from desdeo.problem.schema import Problem

SUPPORTED_VAR_DIMENSIONS = ["scalar"]


def _substitute(expr: sp.Expr, *maps: "dict | None") -> sp.Expr:
    """Substitute each of the given symbol-to-expression maps into an expression."""
    for mapping in maps:
        if mapping:
            expr = expr.subs(mapping, evaluate=False)
    return expr


def _resolve_kind(expressions: "dict | None", *maps: "dict | None") -> "dict | None":
    """Substitute *maps* into each expression of one kind of problem element.

    Elements are resolved in declaration order and each one also has the already
    resolved elements of its own kind substituted into it.  A scalarization function
    may therefore be defined in terms of one declared before it, as in the other
    evaluators.  Only backward references resolve; a reference to an element declared
    later stays unsubstituted and is caught when the expressions are checked.

    Args:
        expressions: symbol-to-expression map for one kind of element, or None.
        *maps: substitution maps to apply, in order, before the same-kind pass.

    Returns:
        A new symbol-to-expression map, or None if *expressions* was None.
    """
    if expressions is None:
        return None

    resolved: dict[str, sp.Expr] = {}
    for symbol, expr in expressions.items():
        resolved[symbol] = _substitute(expr, *maps, resolved)

    return resolved


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

        # Resolve every kind of expression in the order the other evaluators build them --
        # extra functions, objectives, scalarization functions, then constraints.  Each kind
        # may reference the kinds resolved before it, and earlier elements of its own kind.
        _extra_expressions = _resolve_kind(self.extra_expressions, self.constant_expressions)

        _objective_expressions = _resolve_kind(
            self.objective_expressions, self.constant_expressions, _extra_expressions
        )

        # always minimized objective expressions
        _objective_expressions_min = {
            f"{obj.symbol}_min": -_objective_expressions[obj.symbol]
            if obj.maximize
            else _objective_expressions[obj.symbol]
            for obj in problem.objectives
        }

        _scalarization_expressions = _resolve_kind(
            self.scalarization_expressions,
            self.constant_expressions,
            _extra_expressions,
            _objective_expressions,
            _objective_expressions_min,
        )

        # Constraints are resolved last, so that a constraint may reference a scalarization
        # function.  The scenario tools generate exactly that: aggregating a scalarization
        # with add_worst_case_robust bounds each per-leaf scalarization in a constraint.
        _constraint_expressions = _resolve_kind(
            self.constraint_expressions,
            self.constant_expressions,
            _extra_expressions,
            _objective_expressions,
            _objective_expressions_min,
            _scalarization_expressions,
        )

        # Every expression must now be in terms of the decision variables alone.  A symbol
        # that survived substitution is a reference that could not be resolved -- typically
        # to an element declared later.  sympy's lambdify would silently close over it and
        # return an unevaluated expression instead of a number, so reject it here.
        self._check_fully_substituted(
            _extra_expressions,
            _objective_expressions,
            _objective_expressions_min,
            _constraint_expressions,
            _scalarization_expressions,
        )

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

    def _check_fully_substituted(self, *expression_maps: "dict | None") -> None:
        """Verify that no expression refers to anything but the decision variables.

        Args:
            *expression_maps: the resolved symbol-to-expression maps to check.

        Raises:
            SympyEvaluatorError: if any expression still contains an unresolved symbol.
        """
        known = set(self.variable_symbols)
        for expressions in expression_maps:
            for symbol, expr in (expressions or {}).items():
                unresolved = sorted(str(s) for s in getattr(expr, "free_symbols", set()) if str(s) not in known)
                if unresolved:
                    msg = (
                        f"The expression of '{symbol}' still refers to {unresolved} after substitution. "
                        "Expressions may only reference the decision variables and elements declared "
                        "before them."
                    )
                    raise SympyEvaluatorError(msg)

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
