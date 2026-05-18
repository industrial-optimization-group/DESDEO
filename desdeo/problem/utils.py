"""Various utilities used across the framework related to the Problem formulation."""

import itertools
import warnings
from functools import reduce

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
        constraint (Constraint): the constraint to soften. Must have ``func`` defined.
        symbol (str): symbol for the constraint violation objective. Defaults to
            ``"constraint_violation"``.
        lte_violation_symbol (str | None): symbol for the LTE slack variable. Defaults
            to ``f"_{constraint.symbol}_lte_violation"``.
        gte_violation_symbol (str | None): symbol for the GTE slack variable (only used
            for ``=`` constraints). Defaults to
            ``f"_{constraint.symbol}_gte_violation"``.

    Raises:
        ProblemUtilsError: if ``constraint.func`` is ``None``.

    Returns:
        tuple[Problem, str]: a copy of the problem with the soft constraint and
            violation objective added (or updated), and the symbol of the violation
            objective.
    """
    if constraint.func is None:
        msg = f"Cannot soften constraint '{constraint.symbol}': its 'func' field is None."
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
        )
        new_objectives = [*existing_objectives, violation_objective]

    # Append the modified constraint to the problem's constraint list
    existing_constraints = list(problem.constraints) if problem.constraints is not None else []
    new_constraints = [*existing_constraints, modified_constraint]

    new_problem = problem.model_copy(
        update={
            "variables": new_variables,
            "objectives": new_objectives,
            "constraints": new_constraints,
        }
    )

    return new_problem, symbol
