"""Defines a Polars-based evaluator."""

from enum import Enum

import numpy as np
import polars as pl

from desdeo.problem.json_parser import MathParser, replace_str
from desdeo.problem.schema import (
    Constant,
    ObjectiveTypeEnum,
    Problem,
    TensorConstant,
    TensorVariable,
    Variable,
)

SUPPORTED_EVALUATOR_MODES = ["variables", "discrete"]
SUPPORTED_VAR_DIMENSIONS = ["scalar", "vector"]


class PolarsEvaluatorModesEnum(str, Enum):
    """Defines the supported modes for the PolarsEvaluator."""

    variables = "variables"
    """Indicates that the evaluator should expect decision variables vectors and
    evaluate the problem with them."""
    discrete = "discrete"
    """Indicates that the problem is defined by discrete decision variable
    vector and objective vector pairs and those should be evaluated. In this
    mode, the evaluator does not expect any decision variables as arguments when
    evaluating."""
    mixed = "mixed"
    """Indicates that the problem has analytical and simulator and/or surrogate
    based objectives, constraints and extra functions. In this mode, the evaluator
    only handles data-based and analytical functions. For data-bsed objectives,
    it assumes that the variables are to be evaluated by finding the closest
    variables values in the data compare to the input, and evaluating the result
    to be the matching objective function values that match to the closest
    variable values found.  The evaluator should expect decision variables
    vectors and evaluate the problem with them."""


class PolarsEvaluatorError(Exception):
    """Error raised when exceptions are encountered in an PolarsEvaluator."""


class VariableDimensionEnum(str, Enum):
    """An enumerator for the possible dimensions of the variables of a problem."""

    scalar = "scalar"
    """All variables are scalar valued."""
    vector = "vector"
    """Highest dimensional variable is a vector."""
    tensor = "tensor"
    """Some variable has more dimensions."""


def variable_dimension_enumerate(problem: Problem) -> VariableDimensionEnum:
    """Return a VariableDimensionEnum based on the problems variables' dimensions.

    This is needed as different evaluators and solvers can handle different dimensional variables.

    If there are no TensorVariables in the problem, will return scalar.
    If there are, at the highest, one dimensional TensorVariables, will return vector.
    Else, there is at least a TensorVariable with a higher dimension, will return tensor.

    Args:
        problem (Problem): The problem being solved or evaluated.

    Returns:
        VariableDimensionEnum: The enumeration of the problems variable dimensions.
    """
    enum = VariableDimensionEnum.scalar
    for var in problem.variables:
        if isinstance(var, TensorVariable):
            if len(var.shape) == 1 or len(var.shape) == 2 and not (var.shape[0] > 1 and var.shape[1] > 1):  # noqa: PLR2004
                enum = VariableDimensionEnum.vector
            else:
                return VariableDimensionEnum.tensor
    return enum


class PolarsEvaluator:
    """A class for creating Polars-based evaluators for multiobjective optimization problems.

    The evaluator is to be used with different optimizers. PolarsEvaluator is specifically
    for solvers that do not require an exact formulation of the problem, but rather work
    solely on the input and output values of the problem being solved. This evaluator might not
    be suitable for computationally expensive problems, or mixed-integer problems. This
    evaluator is suitable for many Python-based solvers.
    """

    ### Initialization (no need for decision variables yet)
    # 1. Create a math parser with parser type 'evaluator_type'. Defaults to 'polars'.
    # 2. Check for any constants in the definition of the problem. Replace the constants, if they exist,
    #    with their numerical values in all the function expressions found in problem.
    # 3. Parse the function expressions into a dataframe.

    ### Evaluating (we have decision variables to evaluate problem)
    # 1. Evaluate the extra functions (if any) in the dataframe with the decision variables. Store the results
    #    in new columns of the dataframe.
    # 2. Evaluate the objective functions based on the decision variables and the extra function values (if any).
    #    Store the results in the dataframe in their own columns.
    # 3. Evaluate the constraints (if any) based on the decision variables and extra function values (if any).
    #    Store the results in the dataframe in their own columns.
    # 4. Evalute the scalarization functions (if any) based on the objective function values and extra function values
    #    (if any). Store the results in the dataframe in their own columns.
    # 5. Return a pydantic dataclass with the results (decision variables, objective function values, constraint values,
    #    and scalarization function valeus).
    # 6. End.

    def __init__(self, problem: Problem, evaluator_mode: PolarsEvaluatorModesEnum = PolarsEvaluatorModesEnum.variables):
        """Create a Polars-based evaluator for a multiobjective optimization problem.

        By default, the evaluator expects a set of decision variables to
        evaluate the given problem.  However, if the problem is purely based on
        data (e.g., it represents an approximation of a Pareto optimal front),
        then the evaluator should be run in 'discrete' mode instead. In this
        mode, it will return the whole problem with all of its objectives,
        constraints, and scalarization functions evaluated with the current data
        representing the problem.

        Args:
            problem (Problem): The problem as a pydantic 'Problem' data class.
            evaluator_mode (str): The mode of evaluator used to parse the problem into a format
                that can be evaluated. Default 'variables'.
        """
        # Create a MathParser of type 'evaluator_type'.
        if evaluator_mode not in PolarsEvaluatorModesEnum:
            msg = (
                f"The provided 'evaluator_mode' '{evaluator_mode}' is not supported."
                f" Must be one of {PolarsEvaluatorModesEnum}."
            )
            raise PolarsEvaluatorError(msg)

        self.evaluator_mode = evaluator_mode

        self.problem = problem
        # Gather any constants of the problem definition.
        self.problem_constants = problem.constants
        # Gather the objective functions
        if evaluator_mode == PolarsEvaluatorModesEnum.mixed:
            self.problem_objectives = [
                objective
                for objective in problem.objectives
                if objective.objective_type in [ObjectiveTypeEnum.analytical, ObjectiveTypeEnum.data_based]
            ]
        else:
            self.problem_objectives = problem.objectives
        # Gather any constraints
        self.problem_constraints = problem.constraints
        # Gather any extra functions
        self.problem_extra = problem.extra_funcs
        # Gather any scalarization functions
        self.problem_scalarization = problem.scalarization_funcs
        # Gather the decision variable symbols defined in the problem
        self.problem_variable_symbols = [var.symbol for var in problem.variables]
        # The discrete definition of (some) objectives
        self.discrete_representation = problem.discrete_representation

        # The below 'expressions' are list of tuples with symbol and expressions pairs, as (symbol, expression)
        # These must be defined in a specialized initialization step, see further below for an example.
        # Symbol and expressions pairs of the objective functions
        self.objective_expressions = None
        # Symbol and expressions pairs of any constraints
        self.constraint_expressions = None
        # Symbol and expressions pairs of any extra functions
        self.extra_expressions = None
        # Symbol and expression pairs of any scalarization functions
        self.scalarization_expressions = None
        # Store TensorConstants in a dict
        self.tensor_constants = None

        # Note: `self.parser` is assumed to be set before continuing the initialization.
        self.parser = MathParser()
        self._polars_init()

        # Note, when calling an evaluate method, it is assumed the problem has been fully parsed.
        if self.evaluator_mode in [PolarsEvaluatorModesEnum.variables, PolarsEvaluatorModesEnum.mixed]:
            self.evaluate = self._polars_evaluate
            self.evaluate_flat = self._polars_evaluate_flat
        elif self.evaluator_mode == PolarsEvaluatorModesEnum.discrete:
            self.evaluate = self._from_discrete_data
        else:
            msg = (
                f"Provided 'evaluator_mode' {evaluator_mode} not supported. Must be one of {PolarsEvaluatorModesEnum}."
            )

    def _polars_init(self):  # noqa: C901, PLR0912
        """Initialization of the evaluator for parser type 'polars'."""
        # If any constants are defined in problem, replace their symbol with the defined numerical
        # value in all the function expressions found in the Problem.
        if self.problem_constants is not None:
            # Objectives are always defined, cannot be None
            parsed_obj_funcs = {}
            for obj in self.problem_objectives:
                if obj.objective_type == ObjectiveTypeEnum.analytical:
                    # if analytical proceed with replacing the symbols.
                    tmp = obj.func

                    # replace regular constants, skip TensorConstants
                    for c in self.problem_constants:
                        if isinstance(c, Constant):
                            tmp = replace_str(tmp, c.symbol, c.value)

                    parsed_obj_funcs[f"{obj.symbol}"] = tmp

                elif obj.objective_type == ObjectiveTypeEnum.data_based:
                    # data-based objective
                    parsed_obj_funcs[f"{obj.symbol}"] = None
                else:
                    msg = (
                        f"Incorrect objective-type {obj.objective_type} encountered. "
                        f"Must be one of {ObjectiveTypeEnum}"
                    )
                    raise PolarsEvaluatorError(msg)

            # Do the same for any constraint expressions as well.
            if self.problem_constraints is not None:
                parsed_cons_funcs: dict | None = {}
                for con in self.problem_constraints:
                    tmp = con.func

                    # replace regular constants, skip TensorConstants
                    for c in self.problem_constants:
                        if isinstance(c, Constant):
                            tmp = replace_str(tmp, c.symbol, c.value)

                    parsed_cons_funcs[f"{con.symbol}"] = tmp
            else:
                parsed_cons_funcs = None

            # Do the same for any extra functions
            parsed_extra_funcs: dict | None = {}
            if self.problem_extra is not None:
                for extra in self.problem_extra:
                    tmp = extra.func

                    # replace regular constants, skip TensorConstants
                    for c in self.problem_constants:
                        if isinstance(c, Constant):
                            tmp = replace_str(tmp, c.symbol, c.value)

                    parsed_extra_funcs[f"{extra.symbol}"] = tmp
            else:
                parsed_extra_funcs = None

            # Do the same for any scalarization functions
            parsed_scal_funcs: dict | None = {}
            if self.problem_scalarization is not None:
                for scal in self.problem_scalarization:
                    tmp = scal.func

                    # replace regular constants, skip TensorConstants
                    for c in self.problem_constants:
                        if isinstance(c, Constant):
                            tmp = replace_str(tmp, c.symbol, c.value)

                    parsed_scal_funcs[f"{scal.symbol}"] = tmp
            else:
                parsed_scal_funcs = None

            # Check for TensorConstants
            for c in self.problem_constants:
                if isinstance(c, TensorConstant):
                    if self.tensor_constants is None:
                        self.tensor_constants = {}
                    self.tensor_constants[c.symbol] = np.array(c.get_values())
        else:
            # no constants defined, just collect all expressions as they are
            parsed_obj_funcs = {f"{objective.symbol}": objective.func for objective in self.problem_objectives}

            if self.problem_constraints is not None:
                parsed_cons_funcs = {f"{constraint.symbol}": constraint.func for constraint in self.problem_constraints}
            else:
                parsed_cons_funcs = None

            if self.problem_extra is not None:
                parsed_extra_funcs = {f"{extra.symbol}": extra.func for extra in self.problem_extra}
            else:
                parsed_extra_funcs = None

            if self.problem_scalarization is not None:
                parsed_scal_funcs = {f"{scal.symbol}": scal.func for scal in self.problem_scalarization}
            else:
                parsed_scal_funcs = None

        # Parse all functions into expressions. These are stored as tuples, as (symbol, parsed expression)
        # parse objectives
        # If no expression is given (data-based objective, then the expression is set to be 'None')
        self.objective_expressions = [
            (symbol, self.parser.parse(expression)) if expression is not None else (symbol, None)
            for symbol, expression in parsed_obj_funcs.items()
        ]

        # parse constraints, if any
        # if a constraint is simulator or surrogate based (expression is None), set the "parsed" expression as None
        if parsed_cons_funcs is not None:
            self.constraint_expressions = [
                (symbol, self.parser.parse(expression)) if expression is not None else (symbol, None)
                for symbol, expression in parsed_cons_funcs.items()
            ]
        else:
            self.constraint_expressions = None

        # parse extra functions, if any
        # if an extra function is simulator or surrogate based (expression is None), set the "parsed" expression as None
        if parsed_extra_funcs is not None:
            self.extra_expressions = [
                (symbol, self.parser.parse(expression)) if expression is not None else (symbol, None)
                for symbol, expression in parsed_extra_funcs.items()
            ]
        else:
            self.extra_expressions = None

        # parse scalarization functions, if any
        if parsed_scal_funcs is not None:
            self.scalarization_expressions = [
                (symbol, self.parser.parse(expression)) for symbol, expression in parsed_scal_funcs.items()
            ]
        else:
            self.scalarization_expressions = None

        # store the symbol and min or max multiplier as well (symbol, min/max multiplier [1 | -1])
        self.objective_mix_max_mult = [
            (objective.symbol, -1 if objective.maximize else 1) for objective in self.problem_objectives
        ]

        # create dataframe with the discrete representation, if any exists
        if self.discrete_representation is not None:
            self.discrete_df = pl.DataFrame(
                {**self.discrete_representation.variable_values, **self.discrete_representation.objective_values}
            )
        else:
            self.discrete_df = None

    def _polars_evaluate(
        self,
        xs: pl.DataFrame | dict[str, list[float | int | bool]],
    ) -> pl.DataFrame:
        """Evaluate the problem with the given decision variable values utilizing a polars dataframe.

        Args:
            xs (pl.DataFrame | dict[str, list[float | int | bool]]): a Polars dataframe or
                dict with the decision variable symbols as the columns (keys)
                followed by the corresponding decision variable values stored in
                an array (list). The symbols must match the symbols defined for
                the decision variables defined in the `Problem` being solved.
                Each column (list) in the dataframe (dict) should contain the same number of values.

        Returns:
            pl.DataFrame: the polars dataframe with the computed results.

        Note:
            At least `self.objective_expressions` must be defined before calling this method.
        """
        # An aggregate dataframe to store intermediate evaluation results.
        # agg_df = pl.DataFrame({key: np.array(value) for key, value in xs.items()})
        agg_df = pl.DataFrame(
            xs,
            schema=[
                (var.symbol, pl.Float64 if isinstance(var, Variable) else pl.Array(pl.Float64, tuple(var.shape)))
                for var in self.problem.variables
            ],
        )  # need to make sure to provide schema for tensor variables of type Array

        # Deal with TensorConstant
        # agg_df.with_columns(pl.Series(np.array(2*[self.tensor_constants["W"]])).alias("W"))
        if self.tensor_constants is not None:
            for tc_symbol in self.tensor_constants:
                agg_df = agg_df.with_columns(
                    pl.Series(np.array(agg_df.height * [self.tensor_constants[tc_symbol]])).alias(tc_symbol)
                )

        # Evaluate any extra functions and put the results in the aggregate dataframe.
        # If an extra function is simulator or surrogate based (expression None), skip it here
        if self.extra_expressions is not None:
            for symbol, expr in self.extra_expressions:
                if expr is not None:
                    # expression given
                    extra_column = agg_df.select(expr.alias(symbol))
                    agg_df = agg_df.hstack(extra_column)

        # Evaluate the objective functions and put the results in the aggregate dataframe.
        # obj_columns = agg_df.select(*[expr.alias(symbol) for symbol, expr in self.objective_expressions])
        # agg_df = agg_df.hstack(obj_columns)

        for symbol, expr in self.objective_expressions:
            if expr is not None:
                # expression given
                obj_col = agg_df.select(expr.alias(symbol))
                agg_df = agg_df.hstack(obj_col)
            # elif self.evaluator_mode != PolarsEvaluatorModesEnum.mixed:
            else:
                # expr is None and there are no no simulator or surrogate based objectives,
                # therefore we must get the objective function's value somehow else, usually from data
                obj_col = find_closest_points(agg_df, self.discrete_df, self.problem_variable_symbols, symbol)
                agg_df = agg_df.hstack(obj_col)

        # Evaluate the minimization form of the objective functions
        # Note that the column name of these should be 'the objective function's symbol'_min
        # e.g., 'f_1' -> 'f_1_min'
        min_obj_columns = agg_df.select(
            *[
                (min_max_mult * pl.col(f"{symbol}")).alias(f"{symbol}_min")
                for symbol, min_max_mult in self.objective_mix_max_mult
            ]
        )
        agg_df = agg_df.hstack(min_obj_columns)

        # Evaluate any constraints and put the results in the aggregate dataframe
        # If a constraint is simulator or surrogate based (expression None), skip it here
        if self.constraint_expressions is not None:
            for symbol, expr in self.constraint_expressions:
                if expr is not None:
                    # expression given
                    cons_columns = agg_df.select(expr.alias(symbol))
                    agg_df = agg_df.hstack(cons_columns)

        # Evaluate any scalarization functions and put the result in the aggregate dataframe
        if self.scalarization_expressions is not None:
            scal_columns = agg_df.select(*[expr.alias(symbol) for symbol, expr in self.scalarization_expressions])
            agg_df = agg_df.hstack(scal_columns)

        # return the dataframe and let the solver figure it out
        return agg_df

    def _polars_evaluate_flat(
        self,
        xs: pl.DataFrame | dict[str, list[float | int | bool]],
    ) -> pl.DataFrame:
        """Evaluate the problem with flattened variables.

        Args:
            xs (pl.DataFrame | dict[str, list[float  |  int  |  bool]]): a polars dataframe
                or dict with flattened variables.
                E.g., if the original problem has a tensor variable 'X' with shape (2,2),
                then the input is expected to have entries with columns (keys) 'X_1_1', 'X_1_2',
                'X_2_1', and 'X_2_2'. The input is rebuilt and passed to
                `self._evaluate`.

        Note:
            Each flattened variable is assumed to contain the same number of samples.
                This means that if the entry 'X_1_1' of `xs` is, for example
                `[1,2,3]`, this means that 'X_1_1' and all the other flattened
                variables have three samples. This means also that the original
                problem will be evaluated with a tensor variable with shape (2,2)
                and three samples,
                e.g., 'X=[[[1, 1], [1,1]], [[2, 2], [2, 2]], [[3, 3], [3, 3]]]'.

        Returns:
            pl.DataFrame: a dataframe with the original problem's evaluated functions.
        """
        # Assume all variables have the same number of samples
        if isinstance(xs, dict):
            xs = pl.DataFrame(xs)

        unflattened_xs = pl.DataFrame()

        # iterate over the variables of the problem
        for var in self.problem.variables:
            if isinstance(var, TensorVariable):
                # construct the tensor variable

                unflattened_xs = unflattened_xs.with_columns(
                    xs.select(pl.concat_arr(f"^{var.symbol}_.*$").alias(var.symbol).reshape((1, *var.shape)))
                )

            else:
                # else, proceed normally
                unflattened_xs = unflattened_xs.with_columns(xs[var.symbol])

        # return result of regular evaluate
        return self.evaluate(unflattened_xs)

    def _from_discrete_data(self) -> pl.DataFrame:
        """Evaluates the problem based on its discrete representation only.

        Assumes that all the objective functions in the problem are of type 'data-based'.
        In this case, the problem is evaluated based on its current discrete representation. Therefore,
        no decision variable values are expected.

        Returns:
            pl.DataFrame: a polars dataframe with the evaluation results.
        """
        agg_df = self.discrete_df.clone()

        # Evaluate any extra functions and put the results in the aggregate dataframe.
        if self.extra_expressions is not None:
            extra_columns = agg_df.select(*[expr.alias(symbol) for symbol, expr in self.extra_expressions])
            agg_df = agg_df.hstack(extra_columns)

        # Evaluate the minimization form of the objective functions
        # Note that the column name of these should be 'the objective function's symbol'_min
        # e.g., 'f_1' -> 'f_1_min'
        min_obj_columns = agg_df.select(
            *[
                (min_max_mult * pl.col(f"{symbol}")).alias(f"{symbol}_min")
                for symbol, min_max_mult in self.objective_mix_max_mult
            ]
        )

        agg_df = agg_df.hstack(min_obj_columns)

        # Evaluate any constraints and put the results in the aggregate dataframe
        if self.constraint_expressions is not None:
            cons_columns = agg_df.select(*[expr.alias(symbol) for symbol, expr in self.constraint_expressions])
            agg_df = agg_df.hstack(cons_columns)

        # Evaluate any scalarization functions and put the result in the aggregate dataframe
        if self.scalarization_expressions is not None:
            scal_columns = agg_df.select(*[expr.alias(symbol) for symbol, expr in self.scalarization_expressions])
            agg_df = agg_df.hstack(scal_columns)

        # no more processing needed, it is assumed a solver will handle the rest
        return agg_df


def find_closest_points(
    xs: pl.DataFrame, discrete_df: pl.DataFrame, variable_symbols: list[str], objective_symbol: list[str]
) -> pl.DataFrame:
    """Finds the closest points between the variable columns in xs and discrete_df.

    For each row in xs, compares the `variable_symbols` columns and find the closest
    point in `discrete_df`. Returns the objective value in the `objective_symbol` column in
    `discrete_df` for each variable defined in `xs`, where the objective value
    corresponds to the closest point of each variable in `xs` compared to `discrete_df`.

    Both `xs` and `discrete_df` must have the columns `variable_symbols`. `discrete_df` must
    also have the column `objective_symbol`.

    Args:
        xs (pl.DataFrame): a polars dataframe with the variable values we are
            interested in finding the closest corresponding variable values in
            `discrete_df`.
        discrete_df (pl.DataFrame): a polars dataframe to compare the rows in `xs` to.
        variable_symbols (list[str]): the names of the columns with decision variable values.
        objective_symbol (str): the name of the column in `discrete_df` that has the objective function values.

    Returns:
        pl.DataFrame: a dataframe with the columns `objective_symbol` with the
            objective function value that corresponds to each decision variable
            vector in `xs`.
    """
    xs_vars_only = xs[variable_symbols]

    results = []

    for row in xs_vars_only.rows(named=True):
        distance_expr = (
            sum((pl.col(var_symbol) - row[var_symbol]) ** 2 for var_symbol in variable_symbols).sqrt().alias("distance")
        )

        combined_df = discrete_df.with_columns(distance_expr)

        closest = combined_df.sort("distance").head(1)

        results.append(closest[f"{objective_symbol}"][0])

    return pl.DataFrame({f"{objective_symbol}": results})
