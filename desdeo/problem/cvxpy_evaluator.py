"""Defines an evaluator compatible with the Problem JSON format and transforms it into a CVXPY problem."""

import warnings

import cvxpy as cp
import numpy as np

from desdeo.problem.json_parser import FormatEnum, MathParser
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    Objective,
    Problem,
    ScalarizationFunction,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)


class CVXPYEvaluatorError(Exception):
    """Raised when an error within the CVXPYEvaluator class is encountered."""


class CVXPYEvaluatorWarning(UserWarning):
    """Raised when the problem contains features that are poorly supported in cvxpy."""


class CVXPYEvaluator:
    """Defines an evaluator that transforms an instance of Problem into a CVXPY problem."""

    variables: dict[str, cp.Variable]
    parameters: dict[str, cp.Parameter]
    constraints: dict[str, cp.Constraint]
    constraint_expressions: dict[str, cp.Expression]
    objective_functions: dict[str, cp.Expression]
    scalarizations: dict[str, cp.Expression]
    extra_functions: dict[str, cp.Expression]
    constants: dict[str, int | float | list[int] | list[float]]

    problem_model: cp.Problem
    objective_expr: cp.Expression | None

    def __init__(self, problem: Problem):
        """Initialized the evaluator.

        Args:
            problem (Problem): the problem to be transformed into a CVXPY problem.
        """
        self.objective_functions = {}
        self.scalarizations = {}
        self.extra_functions = {}
        self.constants = {}
        self.variables = {}
        self.parameters = {}
        self.constraints = {}
        self.constraint_expressions = {}
        self.objective_expr = None
        self.problem_model = None

        # set the parser
        self.parse = MathParser(to_format=FormatEnum.cvxpy).parse

        # Add variables
        self.variables = self.init_variables(problem)

        # Add constants as parameters, if any
        if problem.constants is not None:
            self.parameters, self.constants = self.init_parameters(problem)

        # Add extra expressions, if any
        if problem.extra_funcs is not None:
            self.extra_functions = self.init_extras(problem)

        # Add objective function expressions
        self.objective_functions = self.init_objectives(problem)

        # Add scalarization functions, if any
        if problem.scalarization_funcs is not None:
            self.scalarizations = self.init_scalarizations(problem)

        # Add constraints, if any
        if problem.constraints is not None:
            self.constraints = self.init_constraints(problem)

        self.problem = problem

    def init_variables(self, problem: Problem) -> dict[str, cp.Variable]:
        """Add variables to the CVXPY problem.

        Args:
            problem (Problem): problem from which to extract the variables.

        Raises:
            CVXPYEvaluatorError: when a problem in extracting the variables is encountered.
                I.e., the variables are of a non supported type.

        Returns:
            dict[str, cp.Variable]: the variables for the problem.
        """
        for var in problem.variables:
            self.add_variable(var)
        return self.variables

    def init_parameters(
        self, problem: Problem
    ) -> tuple[dict[str, cp.Parameter], dict[str, int | float | list[int] | list[float]]]:
        """Add constants as CVXPY parameters.

        CVXPY uses parameters for values that can be changed without redefining the problem.
        This allows constants to be updated between solves.

        Args:
            problem (Problem): problem from which to extract the constants.

        Raises:
            CVXPYEvaluatorError: when the domain of a constant cannot be figured out.

        Returns:
            tuple: a tuple containing (parameters dict, constants dict).
        """
        parameters: dict[str, cp.Parameter] = {}
        constants: dict[str, int | float | list[int] | list[float]] = {}

        for con in problem.constants:
            if isinstance(con, Constant):
                param = cp.Parameter(name=con.symbol, nonneg=con.value >= 0)
                param.value = con.value
                parameters[con.symbol] = param
                constants[con.symbol] = con.value
            elif isinstance(con, TensorConstant):
                values = con.get_values()
                param = cp.Parameter(shape=np.array(values).shape, name=con.symbol)
                param.value = np.array(values)
                parameters[con.symbol] = param
                constants[con.symbol] = values

        return parameters, constants

    def init_extras(self, problem: Problem) -> dict[str, cp.Expression]:
        """Add extra function expressions to a CVXPY evaluator.

        Args:
            problem (Problem): problem from which the extract the extra function expressions.

        Returns:
            dict[str, cp.Expression]: a dict containing the extra function expressions.
        """
        extra_functions: dict[str, cp.Expression] = {}

        for extra in problem.extra_funcs:
            extra_functions[extra.symbol] = self.parse(extra.func, callback=self.get_expression_by_name)

        return extra_functions

    def init_objectives(self, problem: Problem) -> dict[str, cp.Expression]:
        """Add objective function expressions to a CVXPY evaluator.

        Does not yet add any actual CVXPY optimization objectives, only creates a dict containing the
        expressions of the objectives.

        Args:
            problem (Problem): problem from which to extract the objective function expresions.

        Returns:
            dict[str, cp.Expression]: dict containing the objective functions.
        """
        for obj in problem.objectives:
            self.add_objective(obj)
        return self.objective_functions

    def init_constraints(self, problem: Problem) -> dict[str, cp.Constraint]:
        """Add constraint expressions to a CVXPY problem.

        Args:
            problem (Problem): the problem from which to extract the constraint function expressions.

        Raises:
            CVXPYEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            dict[str, cp.Constraint]: dict of constraints keyed by symbol.
        """
        for cons in problem.constraints:
            self.add_constraint(cons)
        return self.constraints

    def init_scalarizations(self, problem: Problem) -> dict[str, cp.Expression]:
        """Add scalarization expressions to a CVXPY evaluator.

        Scalarizations work identically to objectives, except they are stored in a different
        dict in the CVXPYEvaluator.

        Args:
            problem (Problem): the problem from which to extract the scalarization function expressions.

        Returns:
            dict[str, cp.Expression]: the dict with the scalarization expressions.
        """
        scalarizations: dict[str, cp.Expression] = {}

        for scal in problem.scalarization_funcs:
            scalarizations[scal.symbol] = self.parse(scal.func, self.get_expression_by_name)

        return scalarizations

    def add_constraint(self, constraint: Constraint) -> cp.Constraint:
        """Add a constraint expression to the CVXPY problem.

        Args:
            constraint (Constraint): the constraint function expression.

        Raises:
            CVXPYEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            cp.Constraint: The CVXPY constraint that was added.
        """
        expr = self.parse(constraint.func, self.get_expression_by_name)
        self.constraint_expressions[constraint.symbol] = expr

        match constraint.cons_type:
            case ConstraintTypeEnum.LTE:
                cvxpy_constraint = expr <= 0
            case ConstraintTypeEnum.EQ:
                cvxpy_constraint = expr == 0
            case _:
                msg = f"Constraint type of {constraint.cons_type} not supported. Must be one of {ConstraintTypeEnum}."
                raise CVXPYEvaluatorError(msg)

        self.constraints[constraint.symbol] = cvxpy_constraint
        return cvxpy_constraint

    def add_objective(self, obj: Objective):
        """Adds an objective function expression to the CVXPY evaluator.

        Does not yet add any actual CVXPY optimization objectives, only adds them to the dict
        containing the expressions of the objectives.

        Args:
            obj (Objective): the objective function expression to be added.
        """
        expr = self.parse(obj.func, self.get_expression_by_name)
        if isinstance(expr, (int, float)):
            warnings.warn(
                "One or more of the problem objectives seems to be a constant.",
                CVXPYEvaluatorWarning,
                stacklevel=2,
            )

        self.objective_functions[obj.symbol] = expr

        # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
        self.objective_functions[f"{obj.symbol}_min"] = -expr if obj.maximize else expr

    def add_scalarization_function(self, scal: ScalarizationFunction):
        """Adds a scalarization expression to the CVXPY evaluator.

        Scalarizations work identically to objectives, except they are stored in a different
        dict in the CVXPYEvaluator.

        Args:
            scal (ScalarizationFunction): The scalarization function to be added.
        """
        self.scalarizations[scal.symbol] = self.parse(scal.func, self.get_expression_by_name)

    def add_variable(self, var: Variable | TensorVariable) -> cp.Variable:
        """Add a variable to the CVXPY evaluator.

        Args:
            var (Variable | TensorVariable): The definition of the variable to be added.

        Raises:
            CVXPYEvaluatorError: when a problem in extracting the variables is encountered.

        Returns:
            cp.Variable: the variable that was added.
        """
        if isinstance(var, Variable):
            # handle regular variables
            lowerbound = var.lowerbound
            upperbound = var.upperbound

            # Set bounds
            bounds = None
            if lowerbound is not None or upperbound is not None:
                lb = lowerbound if lowerbound is not None else -cp.inf
                ub = upperbound if upperbound is not None else cp.inf
                bounds = [lb, ub]

            # figure out the variable type
            match var.variable_type:
                case VariableTypeEnum.integer:
                    # variable is integer
                    cv_var = cp.Variable(integer=True, bounds=bounds, name=var.symbol)
                case VariableTypeEnum.real:
                    # variable is real
                    cv_var = cp.Variable(bounds=bounds, name=var.symbol)
                case VariableTypeEnum.binary:
                    cv_var = cp.Variable(boolean=True, bounds=bounds, name=var.symbol)
                case _:
                    msg = f"Could not figure out the type for variable {var}."
                    raise CVXPYEvaluatorError(msg)

        elif isinstance(var, TensorVariable):
            # handle tensor variables, i.e., vectors etc..
            lowerbounds = var.get_lowerbound_values() if var.lowerbounds is not None else None
            upperbounds = var.get_upperbound_values() if var.upperbounds is not None else None

            # Set bounds
            bounds = None
            if lowerbounds is not None or upperbounds is not None:
                lb = np.array(lowerbounds) if lowerbounds is not None else -np.inf
                ub = np.array(upperbounds) if upperbounds is not None else np.inf
                bounds = [lb, ub]

            # figure out the variable type
            match var.variable_type:
                case VariableTypeEnum.integer:
                    # variable is integer
                    cv_var = cp.Variable(shape=tuple(var.shape), integer=True, bounds=bounds, name=var.symbol)
                case VariableTypeEnum.real:
                    # variable is real
                    cv_var = cp.Variable(shape=tuple(var.shape), bounds=bounds, name=var.symbol)
                case VariableTypeEnum.binary:
                    cv_var = cp.Variable(shape=tuple(var.shape), boolean=True, bounds=bounds, name=var.symbol)
                case _:
                    msg = f"Could not figure out the type for variable {var}."
                    raise CVXPYEvaluatorError(msg)

        self.variables[var.symbol] = cv_var
        return cv_var

    def get_expression_by_name(self, name: str) -> cp.Expression | np.ndarray | int | float:
        """Returns a CVXPY expression corresponding to the name.

        Looks for variables, parameters, objective functions, scalarizations, and extra functions.

        Args:
            name (str): The symbol of the expression.

        Returns:
            cp.Expression | np.ndarray | int | float: A mathematical expression that CVXPY can use.
        """
        if name in self.variables:
            expression = self.variables[name]
        elif name in self.parameters:
            expression = self.parameters[name]
        elif name in self.objective_functions:
            expression = self.objective_functions[name]
        elif name in self.scalarizations:
            expression = self.scalarizations[name]
        elif name in self.extra_functions:
            expression = self.extra_functions[name]
        elif name in self.constants:
            if isinstance(self.constants[name], list):
                expression = np.array(self.constants[name])
            else:
                expression = self.constants[name]
        else:
            msg = f"No expression with name {name} found in the CVXPY model."
            raise CVXPYEvaluatorError(msg)
        return expression

    def get_values(self) -> dict[str, float | int | bool | list[float] | list[int] | np.ndarray]:
        """Get the values from the CVXPY solution in a dict.

        The keys of the dict will be the symbols defined in the problem utilized to initialize the evaluator.
        Can only be called after the problem has been solved.

        Returns:
            dict: a dict with keys equivalent to the symbols defined in self.problem.

        Raises:
            CVXPYEvaluatorError: if the problem has not been solved yet.
        """
        if self.problem_model is None or self.problem_model.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
            msg = "Problem has not been solved yet or did not achieve optimal status."
            raise CVXPYEvaluatorError(msg)

        result_dict = {}

        for var in self.problem.variables:
            value = self.variables[var.symbol].value
            if value is None:
                msg = f"Variable {var.symbol} has not been solved yet."
                raise CVXPYEvaluatorError(msg)
            result_dict[var.symbol] = value

        for obj in self.problem.objectives:
            result_dict[obj.symbol] = self.objective_functions[obj.symbol].value

        if self.problem.constants is not None:
            for con in self.problem.constants:
                result_dict[con.symbol] = self.constants[con.symbol]

        if self.problem.extra_funcs is not None:
            for extra in self.problem.extra_funcs:
                result_dict[extra.symbol] = self.extra_functions[extra.symbol].value

        if self.problem.scalarization_funcs is not None:
            for scal in self.problem.scalarization_funcs:
                result_dict[scal.symbol] = self.scalarizations[scal.symbol].value

        if self.problem.constraints is not None:
            for con in self.problem.constraints:
                result_dict[con.symbol] = self.constraint_expressions[con.symbol].value

        return result_dict

    def set_optimization_target(self, target: str):
        """Sets an optimization objective for the CVXPY problem.

        Args:
            target (str): a str representing a symbol. Needs to match an objective function or scalarization

        Raises:
            CVXPYEvaluatorError: the given target was not found in the evaluator.
        """
        if target in self.objective_functions:
            objective = self.problem.get_objective(symbol=target, copy=False)
            maximize = False if objective is None else bool(objective.maximize)
        elif target in self.scalarizations:
            maximize = False
        else:
            msg = f"The CVXPY model has no objective or scalarization named {target}."
            raise CVXPYEvaluatorError(msg)

        obj_expr = self.get_expression_by_name(target)

        objective = cp.Maximize(obj_expr) if maximize else cp.Minimize(obj_expr)

        self.objective_expr = objective
        self.problem_model = cp.Problem(objective, list(self.constraints.values()))

    def solve(self, **kwargs):
        """Solve the CVXPY problem.

        Args:
            **kwargs: additional arguments to pass to cp.Problem.solve().
        """
        if self.problem_model is None:
            msg = "No optimization target has been set. Call set_optimization_target() first."
            raise CVXPYEvaluatorError(msg)

        if self.problem_model.is_dcp():
            self.problem_model.solve(**kwargs)
        elif self.problem_model.is_dgp():
            kwargs["gp"] = True
            self.problem_model.solve(**kwargs)
        else:
            warnings.warn(
                "The problem does not appear to be DCP or DGP. CVXPY may not be able to solve it.",
                CVXPYEvaluatorWarning,
                stacklevel=2,
            )
            self.problem_model.solve(**kwargs)

    def update_parameter(self, symbol: str, value: int | float | list[int] | list[float] | np.ndarray):
        """Update the value of a parameter (constant).

        Args:
            symbol (str): the symbol of the parameter to update.
            value: the new value for the parameter.

        Raises:
            CVXPYEvaluatorError: if the parameter does not exist.
        """
        if symbol not in self.parameters:
            msg = f"Parameter {symbol} not found in the evaluator."
            raise CVXPYEvaluatorError(msg)

        self.parameters[symbol].value = value
        if isinstance(value, (list, np.ndarray)):
            self.constants[symbol] = list(value) if isinstance(value, np.ndarray) else value
        else:
            self.constants[symbol] = value
