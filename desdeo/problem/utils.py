"""Various utilities used across the framework related to the Problem formulation."""

import numpy as np
import polars as pl

from desdeo.problem import Problem, TensorConstant, TensorVariable


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


def variable_dict_to_numpy_array(problem: Problem, variable_dict: dict[str, float]) -> np.ndarray:
    """Takes a dict with a decision variable vector and returns a numpy array.

    Takes a dict with the keys being decision variable symbols and the values
    being the corresponding variable values. Returns a numpy array
    with the decision variable values in the same order they have been defined in
    the original problem.

    Args:
        problem (Problem): the problem the objective dict belongs to.
        variable_dict (dict[str, float]): the dict with the decision variable values.

    Returns:
        np.ndarray: a numpy array with the decision variable values in the order they are
            present in problem.
    """
    if isinstance(variable_dict[problem.variables[0].symbol], list):
        if len(variable_dict[problem.variables[0].symbol]) != 1:
            raise ValueError("The variable_dict has multiple values for a decision variable.")
        return np.array([variable_dict[variable.symbol][0] for variable in problem.variables])
    return np.array([variable_dict[variable.symbol] for variable in problem.variables])


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
