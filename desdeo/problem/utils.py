"""Various utilities used across the framework related to the Problem formulation."""

import itertools
import warnings
from functools import reduce

import cvxpy as cp
import numpy as np
import polars as pl

from desdeo.problem import (
    Constraint,
    ConstraintTypeEnum,
    Objective,
    Problem,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.json_parser import FormatEnum, MathParser

# MathJSON operators that are not twice differentiable everywhere (they are discontinuous,
# kinked, or otherwise non-smooth), used by `determine_problem_properties` to flag functions
# that use them, directly or through a reference to another function in the problem.
_NON_SMOOTH_OPERATORS = frozenset({"Abs", "Max", "Min", "Ceil", "Floor"})


class ProblemUtilsError(Exception):
    """Raised when an exception occurs in one of the utils function.

    Raised when an exception occurs in one of the utils functions defined in the Problem module.
    """


def objective_dict_to_numpy_array(problem: Problem, objective_dict: dict[str, float]) -> np.ndarray:
    """Takes a dict with an objective vector and returns a numpy array.

    Takes a dict with the keys being objective function symbols and the values
    being the corresponding objective function values. Returns a numpy array
    with the objective function values in the same order they have been defined
    in the original problem.

    Args:
        problem (Problem): the problem the objective dict belongs to.
        objective_dict (dict[str, float]): the dict with the objective function values.

    Returns:
        np.ndarray: a numpy array with the objective function values in the order they are
            present in problem.
    """
    if isinstance(objective_dict[problem.objectives[0].symbol], list):
        if len(objective_dict[problem.objectives[0].symbol]) != 1:
            raise ValueError("The objective_dict has multiple values for an objective function")
        return np.array([objective_dict[objective.symbol][0] for objective in problem.objectives])
    return np.array([objective_dict[objective.symbol] for objective in problem.objectives])


def numpy_array_to_objective_dict(problem: Problem, numpy_array: np.ndarray) -> dict[str, float]:
    """Takes a numpy array with objective function values and return a dict.

    The reverse of objective_dict_to_numpy_array.

    Args:
        problem (Problem): the problem the numpy array represents an objective vector of.
        numpy_array (np.ndarray): the objective vector as a numpy array. The
            array is squeezed, i.e., axes or length one are removed: [[42]] -> [42].

    Returns:
        dict[str, float]: a dict with keys being objective function symbols and value being
            objective function values.
    """
    return {objective.symbol: np.squeeze(numpy_array).tolist()[i] for i, objective in enumerate(problem.objectives)}


def unflatten_variable_array(problem: Problem, var_array: np.ndarray) -> dict[str, float | list]:
    """Unflatten a numpy array representing decision variable values.

    Unflatten a numpy array that represent decision variable values. It is assumed
    that the unflattened values follow a C-like order when it comes to unflattening
    values for `TensorVariable`s. Note that `var_array` must be of dimension 1.

    Args:
        problem (Problem): the problem instance the decision variables are associated with.
        var_array (np.ndarray): a flat 1D array of numerical values representing
            decision variable values.

    Raises:
        ValueError: `var_array` is of some other dimension that 1.
        IndexError: `var_array` has too few elements given the variables defined in
            the instance of `Problem`.
        TypeError: unsupported variable type encountered in the variables defined in the
            instance of `Problem`.

    Returns:
        dict[str, float | list]: a dict with keys equal to the symbols of the variables
            defined in the `Problem` instance, and values equal to the decision variable
            values as they were defined in `var_array`.
    """
    if (dimension := var_array.ndim) != 1:
        msg = f"The given variable array must have a dimension of 1. Current {dimension=}"
        raise ValueError(msg)

    var_dict = {}
    array_i = 0
    for var in problem.variables:
        if array_i >= len(var_array):
            msg = (
                "End of variable array reached before all variables in the problem were iterated over. "
                f"The variable array is too short with length={len(var_array)}."
            )
            raise IndexError(msg)

        if isinstance(var, Variable):
            # regular variable, just pick it
            var_dict[var.symbol] = var_array[array_i].item()
            array_i += 1
            continue

        if isinstance(var, TensorVariable):
            # tensor variable, pick row-wise from var_array
            slice_length = reduce(lambda x1, x2: x1 * x2, var.shape)  # product of dimensions
            flat_values = var_array[array_i : array_i + slice_length]
            var_dict[var.symbol] = np.reshape(flat_values, var.shape, order="C").tolist()
            array_i += slice_length
            continue

        msg = f"Unsupported variable type {type(var)} encountered."
        raise TypeError(msg)

    # check if values remain in var_array
    if array_i < len(var_array):
        # some values remain, warn user, but do not raise an error
        msg = f"Warning, the variable array had some values that were not unflattened: f{['...', *var_array[array_i:]]}"
        warnings.warn(msg, stacklevel=2)

    # return the variable dict
    return var_dict


def flatten_variable_dict(problem: Problem, variable_dict: dict[str, float | list]) -> np.ndarray:
    """Flatten a dictionary representing variable values of an instance of `Problem` into a numpy array.

    Flattens a dictionary representing variable values of an instance of `Problem` into a numpy array.
    The flattening follows a C-like order. Support the flattening of both `Variable` and `TensorVariable`
    types. Note that it is assumed that no more than one value is defined for each symbol in `variable_dict`
    that correspond to the required shape of the underlying variable type.

    Args:
        problem (Problem): the problem instance the decision variables are associated with.
        variable_dict (dict[str, float  |  list]): a dictionary with its keys being the symbols
            of the variables defined in the instance of `Problem`, and the values corresponding
            to the variables' values.

    Raises:
        ValueError: the `variable_dict` does not contain as its keys one or more of the symbols
            defined for the variables in the instance of `Problem`.
        TypeError: unsupported variable type encountered in the variables defined in the
            instance of `Problem`.

    Returns:
        np.ndarray: a 1D numpy array with the variable values unflattened in C-like order.
    """
    tmp = []
    for var in problem.variables:
        if isinstance(var, Variable):
            # just a regular variable
            if var.symbol not in variable_dict:
                msg = f"The variable_dict is missing values for the variable {var.symbol}."
                raise ValueError(msg)
            tmp.append([variable_dict[var.symbol]])
            continue

        if isinstance(var, TensorVariable):
            # tensor variable
            if var.symbol in variable_dict:
                # tensor variable is defined in the dict as a tensor
                tmp = [*tmp, np.array(variable_dict[var.symbol]).flatten(order="C")]
                continue
            if any(key.startswith(f"{var.symbol}_") for key in variable_dict):
                # tensor variable flattened in the dict
                indices = itertools.product(*[range(1, s + 1) for s in var.shape])
                flat_symbols = [f"{var.symbol}_{'_'.join(map(str, index))}" for index in indices]
                tmp = [*tmp, np.array([variable_dict[s] for s in flat_symbols])]
                continue

            msg = f"The variable dict is missing values for the variable {var.symbol}."
            raise ValueError(msg)

        msg = f"Unsupported variable type {type(var)} encountered."
        raise TypeError(msg)

    return np.concatenate(tmp)


def get_nadir_dict(problem: Problem) -> dict[str, float]:
    """Return a dict representing a problem's nadir point.

    Args:
        problem (Problem): the problem with the nadir point.

    Returns:
        dict[str, float]: key are objective funciton symbols, values are nadir values.
    """
    return {objective.symbol: objective.nadir for objective in problem.objectives}


def get_ideal_dict(problem: Problem) -> dict[str, float]:
    """Return a dict representing a problem's ideal point.

    Args:
        problem (Problem): the problem with the ideal point.

    Returns:
        dict[str, float]: key are objective funciton symbols, values are ideal values.
    """
    return {objective.symbol: objective.ideal for objective in problem.objectives}


def tensor_constant_from_dataframe(
    df: pl.DataFrame, name: str, symbol: str, n_rows: int, column_names: list[str]
) -> TensorConstant:
    """Create a TensorConstant from a Polars dataframe.

    Args:
        df (pl.DataFrame): a Polars dataframe with at least the columns in `column_names`
        name (str): name attribute of the created TensorConstant.
        symbol (str): symbol attribute of the created TensorConstant.
        n_rows (int): the number of rows to read from the dataframe.
        column_names (list[str]): the column names in the dataframe from which
            the constant values will be picked.

    Returns:
        TensorConstant: A TensorConstant instance with values taken from the a given
            Polars dataframe. The shape of the TensorConstant will be
            (`n_rows`, len(`column_names`)).

    Note:
        In the argument `shape` the first element must be either less or equal to the
            number of rows in `df`. The second element in `shape` must be equal
            to the number of element in `column_names`.
    """
    if n_rows > df.shape[0]:
        # not enough rows in df
        msg = f"Requested {n_rows} rows, but the dataframe has only {df.shape[0]} rows."
        raise ProblemUtilsError(msg)

    if len(column_names) > df.shape[1]:
        # not enough cols in df
        msg = f"Requested {len(column_names)} columns, but the dataframe has only {df.shape[1]} columns."
        raise ProblemUtilsError(msg)

    for col in column_names:
        if col not in df.columns:
            msg = f"The requested column '{col}' is not found in the given dataframe with columns {df.columns}."
            raise ProblemUtilsError(msg)

    selected_df = df.select(column_names).head(n_rows)
    selected_values = [selected_df.to_dict()[col_name].to_list() for col_name in column_names]

    return TensorConstant(name=name, symbol=symbol, shape=[n_rows, len(column_names)], values=selected_values)


def add_soft_constraint(
    problem: Problem,
    constraint: Constraint,
    symbol: str = "constraint_violation",
    lte_violation_symbol: str | None = None,
    gte_violation_symbol: str | None = None,
) -> tuple[Problem, str]:
    """Add a constraint as a soft constraint by introducing violation slack variables.

    Adds non-negative slack variables that absorb constraint violations and accumulates
    their sum into a minimization objective (the constraint violation objective). For a
    ``<=`` constraint ``g(x) <= 0`` the modified constraint becomes
    ``g(x) - s_lte <= 0`` where ``s_lte >= 0``. For an ``=`` constraint
    ``g(x) = 0`` the modified constraint becomes
    ``g(x) - s_lte + s_gte = 0`` where both ``s_lte, s_gte >= 0``.

    The constraint violation objective is created if it does not already exist in the
    problem, or updated to include the new slack variables if it does.

    Args:
        problem (Problem): the problem to add the soft constraint to.
        constraint (Constraint): the constraint to add as a soft constraint. Must have ``func`` defined.
        symbol (str): symbol for the constraint violation objective. Defaults to
            ``"constraint_violation"``.
        lte_violation_symbol (str | None): symbol for the LTE slack variable. Defaults
            to ``f"_{constraint.symbol}_lte_violation"``.
        gte_violation_symbol (str | None): symbol for the GTE slack variable (only used
            for ``=`` constraints). Defaults to
            ``f"_{constraint.symbol}_gte_violation"``.

    Raises:
        ProblemUtilsError: if ``constraint.func`` is ``None``, or if a constraint with the
            symbol ``constraint.symbol`` already exists in ``problem``.

    Returns:
        tuple[Problem, str]: a copy of the problem with the soft constraint and
            violation objective added (or updated), and the symbol of the violation
            objective.
    """
    if constraint.func is None:
        msg = f"Cannot create soft constraint '{constraint.symbol}': its 'func' field is None."
        raise ProblemUtilsError(msg)

    if problem.constraints is not None and any(c.symbol == constraint.symbol for c in problem.constraints):
        msg = f"A constraint with the symbol '{constraint.symbol}' already exists in the problem."
        raise ProblemUtilsError(msg)

    if lte_violation_symbol is None:
        lte_violation_symbol = f"_{constraint.symbol}_lte_violation"
    if gte_violation_symbol is None:
        gte_violation_symbol = f"_{constraint.symbol}_gte_violation"

    # Build violation slack variables (continuous, lb=0, no upper bound)
    lte_var = Variable(
        name=f"LTE violation for constraint '{constraint.symbol}'",
        symbol=lte_violation_symbol,
        variable_type=VariableTypeEnum.real,
        lowerbound=0,
        upperbound=None,
        initial_value=0.0,
    )
    new_variables = [*problem.variables, lte_var]
    new_violation_symbols: list[str] = [lte_violation_symbol]

    if constraint.cons_type == ConstraintTypeEnum.EQ:
        gte_var = Variable(
            name=f"GTE violation for constraint '{constraint.symbol}'",
            symbol=gte_violation_symbol,
            variable_type=VariableTypeEnum.real,
            lowerbound=0,
            upperbound=None,
            initial_value=0.0,
        )
        new_variables = [*new_variables, gte_var]
        new_violation_symbols.append(gte_violation_symbol)

    # Build the modified constraint func with violation variables absorbed
    if constraint.cons_type == ConstraintTypeEnum.LTE:
        modified_func = ["Subtract", constraint.func, lte_violation_symbol]
    else:  # EQ
        modified_func = ["Add", ["Subtract", constraint.func, lte_violation_symbol], gte_violation_symbol]

    modified_constraint = constraint.model_copy(update={"func": modified_func})

    # Build the constraint violation objective func for this constraint's slack variables.
    # Use Multiply(1, sym) for a single variable to avoid bare-string backend issues.
    if len(new_violation_symbols) == 1:
        violation_func: list = ["Multiply", 1, new_violation_symbols[0]]
    else:
        violation_func = ["Add", *new_violation_symbols]

    # Update an existing violation objective or create a new one
    existing_objectives = list(problem.objectives)
    violation_obj_idx = next((i for i, obj in enumerate(existing_objectives) if obj.symbol == symbol), None)

    if violation_obj_idx is not None:
        existing_obj = existing_objectives[violation_obj_idx]
        existing_func = existing_obj.func
        # Extend the existing sum; if it already starts with Add, just append.
        if isinstance(existing_func, list) and existing_func[0] == "Add":
            new_violation_func = [*existing_func, *new_violation_symbols]
        else:
            new_violation_func = ["Add", existing_func, *new_violation_symbols]
        updated_obj = existing_obj.model_copy(update={"func": new_violation_func})
        existing_objectives[violation_obj_idx] = updated_obj
        new_objectives = existing_objectives
    else:
        violation_objective = Objective(
            name="Constraint violation",
            symbol=symbol,
            func=violation_func,
            maximize=False,
            # The slack variables are non-negative, so zero violation is attainable by
            # definition and is the ideal.  The nadir has no natural value: the largest
            # violation depends on how far the soft constraints reach outside the
            # feasible region, and computing it would need a solve of its own.  One is a
            # placeholder, meant to be raised once an actual violation is observed, as
            # `desdeo.mcdm.cumulus` does after minimizing the total violation.
            ideal=0.0,
            nadir=1.0,
        )
        new_objectives = [*existing_objectives, violation_objective]

    # Append the modified constraint to the problem's constraint list
    existing_constraints = list(problem.constraints) if problem.constraints is not None else []
    new_constraints = [*existing_constraints, modified_constraint]

    new_problem = Problem.model_validate(
        problem.model_dump(by_alias=True)
        | {
            "variables": new_variables,
            "objectives": new_objectives,
            "constraints": new_constraints,
        }
    )

    return new_problem, symbol


def _cvxpy_symbol_scope(problem: Problem) -> dict[str, object]:
    """Build a symbol-to-cvxpy-expression scope for a problem's decision variables and constants."""
    scope: dict[str, object] = {}

    for var in problem.variables:
        scope[var.symbol] = (
            cp.Variable(shape=tuple(var.shape), name=var.symbol)
            if isinstance(var, TensorVariable)
            else cp.Variable(name=var.symbol)
        )

    if problem.constants is not None:
        for const in problem.constants:
            scope[const.symbol] = np.array(const.get_values()) if isinstance(const, TensorConstant) else const.value

    return scope


def _contains_nonsmooth_operator(node: object, symbol_funcs: dict[str, list], visited: frozenset[str]) -> bool:
    """Check whether a MathJSON expression uses an operator that is not twice differentiable everywhere.

    Recurses into the expression tree, and, whenever a string names a function declared
    elsewhere in the problem (an extra function, objective, scalarization function, or
    constraint), follows that reference too. This way, e.g., an objective built from an
    extra function that uses `Abs` is flagged as not twice differentiable as well.

    Args:
        node: the current MathJSON node being inspected (a list, a symbol/operator
            string, or a literal number).
        symbol_funcs (dict[str, list]): a map from every function symbol declared in the
            problem to its MathJSON expression.
        visited (frozenset[str]): symbols already followed, to guard against cycles.

    Returns:
        bool: `True` if a non-twice-differentiable operator was found.
    """
    if isinstance(node, list):
        return any(_contains_nonsmooth_operator(child, symbol_funcs, visited) for child in node)
    if isinstance(node, str):
        if node in _NON_SMOOTH_OPERATORS:
            return True
        if node in symbol_funcs and node not in visited:
            return _contains_nonsmooth_operator(symbol_funcs[node], symbol_funcs, visited | {node})
    return False


def _cvxpy_linear_and_convex(expr: object) -> tuple[bool, bool]:
    """Determine linearity and convexity from a resolved cvxpy expression.

    Args:
        expr: the expression to inspect, or `None` if it could not be resolved
            (e.g. because it uses an operator cvxpy's DCP atom library does not support,
            such as a trigonometric function).

    Returns:
        tuple[bool, bool]: `(is_linear, is_convex)`. When `expr` could not be resolved,
            both are conservatively `False`: it is better to under-report these properties
            than to claim a function is linear or convex when it is not.
    """
    if isinstance(expr, (int, float)):
        return True, True
    if expr is not None and hasattr(expr, "is_affine"):
        is_linear = bool(expr.is_affine())
        return is_linear, is_linear or bool(expr.is_convex())
    return False, False


def _collect_symbol_funcs(problem: Problem) -> dict[str, list]:
    """Map every function symbol declared in a problem to its MathJSON expression.

    Objectives are also mapped under their `f"{symbol}_min"` alias (the always-minimized
    variant used by scalarization functions and constraints, see `SympyEvaluator`), so that
    a reference to that alias still follows through to the objective's own expression when
    checking for non-smooth operators.
    """
    symbol_funcs: dict[str, list] = {}
    for items in (problem.extra_funcs, problem.objectives, problem.scalarization_funcs, problem.constraints):
        if items is None:
            continue
        for item in items:
            if item.func is not None:
                symbol_funcs[item.symbol] = item.func
                if isinstance(item, Objective):
                    symbol_funcs[f"{item.symbol}_min"] = item.func
    return symbol_funcs


def _resolve_properties(
    symbol: str,
    func: list,
    symbol_funcs: dict[str, list],
    scope: dict[str, object],
    cvxpy_parser: MathParser,
) -> tuple[bool, bool, bool]:
    """Resolve one function's expression in cvxpy and derive its properties.

    As a side effect, stores the resolved cvxpy expression (if any) in `scope` under
    `symbol`, so that functions processed afterwards can reference it in turn.
    """
    try:
        expr = cvxpy_parser.parse(func, callback=scope.__getitem__)
    except Exception:
        expr = None

    is_linear, is_convex = _cvxpy_linear_and_convex(expr)
    is_twice_differentiable = is_linear or not _contains_nonsmooth_operator(func, symbol_funcs, frozenset())

    if expr is not None:
        scope[symbol] = expr

    return is_linear, is_convex, is_twice_differentiable


def _analyze_problem_functions(problem: Problem) -> dict[str, tuple[bool, bool, bool]]:
    """Analyze every analytical function in a problem, in the order the other evaluators resolve them."""
    symbol_funcs = _collect_symbol_funcs(problem)
    cvxpy_parser = MathParser(to_format=FormatEnum.cvxpy)
    scope = _cvxpy_symbol_scope(problem)
    properties: dict[str, tuple[bool, bool, bool]] = {}

    for extra in problem.extra_funcs or []:
        if extra.func is not None:
            properties[extra.symbol] = _resolve_properties(extra.symbol, extra.func, symbol_funcs, scope, cvxpy_parser)

    for obj in problem.objectives:
        if obj.func is None:
            continue
        properties[obj.symbol] = _resolve_properties(obj.symbol, obj.func, symbol_funcs, scope, cvxpy_parser)
        if obj.symbol in scope:
            # Scalarization functions and constraints may reference the always-minimized variant
            # of an objective, as the other evaluators also provide (e.g. SympyEvaluator).
            scope[f"{obj.symbol}_min"] = -scope[obj.symbol] if obj.maximize else scope[obj.symbol]

    for scal in problem.scalarization_funcs or []:
        properties[scal.symbol] = _resolve_properties(scal.symbol, scal.func, symbol_funcs, scope, cvxpy_parser)

    for con in problem.constraints or []:
        if con.func is not None:
            properties[con.symbol] = _resolve_properties(con.symbol, con.func, symbol_funcs, scope, cvxpy_parser)

    return properties


def _with_properties(item, properties: dict[str, tuple[bool, bool, bool]]):
    """Return a copy of a function (objective/constraint/extra/scalarization) with analyzed properties applied."""
    props = properties.get(item.symbol)
    if props is None:
        return item
    is_linear, is_convex, is_twice_differentiable = props
    return item.model_copy(
        update={
            "is_linear": is_linear,
            "is_convex": is_convex,
            "is_twice_differentiable": is_twice_differentiable,
        }
    )


def determine_problem_properties(problem: Problem) -> Problem:
    """Analyze a problem's functions and set their linearity, convexity, and differentiability flags.

    For every analytical function defined in the problem (objectives, constraints, extra
    functions, and scalarization functions), determines whether its expression is linear,
    convex, and twice differentiable, and returns a copy of the problem with the
    corresponding `is_linear`, `is_convex`, and `is_twice_differentiable` fields set
    accordingly. Functions without a `func` expression (data-based, simulator, or
    surrogate functions) are left untouched, as there is no expression to analyze.

    Linearity is checked first, since an affine (linear) function is always both convex
    and twice differentiable, regardless of what the other two checks find. Convexity is
    otherwise determined with cvxpy's DCP curvature rules, applied to the function's
    expression after resolving any other problem functions and constants it references.
    Proving convexity in general is undecidable, and cvxpy's DCP rules only recognize
    convexity that follows from a known composition of convex/concave building blocks, so
    this check can miss functions that are convex. It is deliberately conservative: it may
    report a convex function as not (provably) convex, but should not report a non-convex
    function as convex. Twice differentiability is determined by scanning the function's
    expression, and transitively any function it references, for the `Abs`, `Max`, `Min`,
    `Ceil`, and `Floor` operators, none of which are twice differentiable everywhere.

    Args:
        problem (Problem): the problem whose functions are to be analyzed.

    Returns:
        Problem: a copy of `problem` with the `is_linear`, `is_convex`, and
            `is_twice_differentiable` fields set on each analytical function.
    """
    properties = _analyze_problem_functions(problem)

    return problem.model_copy(
        update={
            "objectives": [_with_properties(obj, properties) for obj in problem.objectives],
            "constraints": [_with_properties(con, properties) for con in problem.constraints]
            if problem.constraints is not None
            else None,
            "extra_funcs": [_with_properties(extra, properties) for extra in problem.extra_funcs]
            if problem.extra_funcs is not None
            else None,
            "scalarization_funcs": [_with_properties(scal, properties) for scal in problem.scalarization_funcs]
            if problem.scalarization_funcs is not None
            else None,
        }
    )


def determine_function_properties(problem: Problem, symbol: str) -> Problem:
    """Analyze a single function of a problem and set its linearity, convexity, and differentiability flags.

    Behaves exactly like `determine_problem_properties`, but only applies the result to
    the one function identified by `symbol` (an objective, constraint, extra function, or
    scalarization function), leaving every other function's flags untouched.

    This matters because the convexity and twice-differentiability checks are
    conservative and can produce false negatives (see `determine_problem_properties`):
    re-running them over the whole problem would silently overwrite flags that may have
    been deliberately set elsewhere from outside knowledge the checks here cannot derive
    on their own. Targeting a single, newly added or changed function avoids that.

    Args:
        problem (Problem): the problem the function belongs to.
        symbol (str): the symbol of the function to analyze.

    Raises:
        ProblemUtilsError: no function with the given symbol and an analyzable `func`
            expression (i.e., not a data-based, simulator, or surrogate function) was
            found in the problem.

    Returns:
        Problem: a copy of `problem` with the `is_linear`, `is_convex`, and
            `is_twice_differentiable` fields set on the identified function only.
    """
    properties = _analyze_problem_functions(problem)

    if symbol in properties:
        for attr in ("objectives", "constraints", "extra_funcs", "scalarization_funcs"):
            items = getattr(problem, attr)
            if items is None:
                continue
            for i, item in enumerate(items):
                if item.symbol == symbol:
                    new_items = [*items[:i], _with_properties(item, properties), *items[i + 1 :]]
                    return problem.model_copy(update={attr: new_items})

    msg = f"No analyzable function with the symbol '{symbol}' was found in the problem."
    raise ProblemUtilsError(msg)
