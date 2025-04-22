"""Defines an evaluator compatible with the Problem JSON format and transforms it into a GurobipyModel."""

from operator import eq as _eq
from operator import le as _le
import warnings

import gurobipy as gp
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
    VariableTypeEnum

)


class GurobipyEvaluatorError(Exception):
    """Raised when an error within the GurobipyEvaluator class is encountered."""


class GurobipyEvaluatorWarning(UserWarning):
    """Raised when the problem contains features that are poorly supported in gurobipy."""


class GurobipyEvaluator:
    """Defines as evaluator that transforms an instance of Problem into a GurobipyModel."""

    # gp.Model does not support these, so the evaluator will handle them
    objective_functions: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr]
    scalarizations: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr]
    extra_functions: dict[
        str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float
    ]
    constants: dict[str, int | float | list[int] | list[float]]

    model: gp.Model

    def __init__(self, problem: Problem):
        """Initialized the evaluator.

        Args:
            problem (Problem): the problem to be transformed in a GurobipyModel.
        """
        self.model = gp.Model(problem.name)
        self.objective_functions = {}
        self.scalarizations = {}
        self.extra_functions = {}
        self.constants = {}
        self.mvars = {}

        # set the parser
        self.parse = MathParser(to_format=FormatEnum.gurobipy).parse

        # Add variables
        self.model = self.init_variables(problem)

        # Add constants, if any
        if problem.constants is not None:
            self.constants = self.init_constants(problem)

        # Add extra expressions, if any
        if problem.extra_funcs is not None:
            self.extra_functions = self.init_extras(problem)

        # Add objective function expressions
        self.objective_functions = self.init_objectives(problem)

        # Add constraints, if any
        if problem.constraints is not None:
            self.model = self.init_constraints(problem)

        # Add scalarization functions, if any
        if problem.scalarization_funcs is not None:
            self.scalarizations = self.init_scalarizations(problem)

        self.problem = problem

    def init_variables(self, problem: Problem) -> gp.Model:
        """Add variables to the GurobipyModel.

        Args:
            problem (Problem): problem from which to extract the variables.

        Raises:
            GurobipyEvaluatorError: when a problem in extracting the variables is encountered.
                I.e., the variables are of a non supported type.

        Returns:
            GurobipyModel: the GurobipyModel with the variables added as attributes.
        """
        for var in problem.variables:
            if isinstance(var, Variable):
                # handle regular variables
                lowerbound = var.lowerbound if var.lowerbound is not None else float("-inf")
                upperbound = var.upperbound if var.upperbound is not None else float("inf")

                # figure out the variable type
                match var.variable_type:
                    case VariableTypeEnum.integer:
                        # variable is integer
                        domain = gp.GRB.INTEGER
                    case VariableTypeEnum.real:
                        # variable is real
                        domain = gp.GRB.CONTINUOUS
                    case VariableTypeEnum.binary:
                        domain = gp.GRB.BINARY
                    case _:
                        msg = f"Could not figure out the type for variable {var}."
                        raise GurobipyEvaluatorError(msg)

                # add the variable to the model
                gvar = self.model.addVar(lb=lowerbound, ub=upperbound, vtype=domain, name=var.symbol)
                # set the initial value, if one has been defined
                if var.initial_value is not None:
                    gvar.setAttr("Start", var.initial_value)

            elif isinstance(var, TensorVariable):
                # handle tensor variables, i.e., vectors etc..
                lowerbounds = var.get_lowerbound_values() if var.lowerbounds is not None else np.full(var.shape, float("-inf")).tolist()
                upperbounds = var.get_upperbound_values() if var.upperbounds is not None else np.full(var.shape, float("inf")).tolist()

                # figure out the variable type
                match var.variable_type:
                    case VariableTypeEnum.integer:
                        # variable is integer
                        domain = gp.GRB.INTEGER
                    case VariableTypeEnum.real:
                        # variable is real
                        domain = gp.GRB.CONTINUOUS
                    case VariableTypeEnum.binary:
                        domain = gp.GRB.BINARY
                    case _:
                        msg = f"Could not figure out the type for variable {var}."
                        raise GurobipyEvaluatorError(msg)

                # add the variable to the model
                gvar = self.model.addMVar(shape=tuple(var.shape), lb=np.array(lowerbounds), ub=np.array(upperbounds), vtype=domain, name=var.symbol)
                # set the initial value, if one has been defined
                if var.initial_values is not None:
                    gvar.setAttr("Start", np.array(var.get_initial_values()))
                self.mvars[var.symbol] = gvar


        # update the model before returning, so that other expressions can reference the variables
        self.model.update()

        return self.model

    def init_constants(self, problem: Problem) -> dict[str, int | float | list[int] | list[float]]:
        """Add constants to a GurobipyEvaluator.

        Gurobi does not really have constants, so this function instead
        stores them in a dict, that is then stored in the evaluator.
        This is necessary to get the MathParser to understand the constants
        used in the problem, but updating them at a later point will not update
        any expression referencing them. The expressions that have been defined
        using these constants will keep using the numeric value of the constant
        at the time when the expression was created.
        Thus, it might be best to avoid using constants if you are intending
        to use the gurobipy solver.

        Args:
            problem (Problem): problem from which to extract the constants.

        Raises:
            GurobipyEvaluatorError: when the domain of a constant cannot be figured out.

        Returns:
            dict[str, int | float]: a dict containing the constants.
        """
        constants: dict[str, int | float | list[int] | list[float]] = {}
        for con in problem.constants:
            if isinstance(con, Constant):
                constants[con.symbol] = con.value
            elif isinstance(con, TensorConstant):
                constants[con.symbol] = con.get_values()

        return constants

    def init_extras(
        self, problem: Problem
    ) -> dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float]:
        """Add extra function expressions to a Gurobipy Model.

        Gurobi does not support extra expressions natively, so this function instead
        stores them in a dict to be used by the evaluator.
        This is necessary to get the MathParser to understand the extra expressions
        used in the problem, but updating them at a later point will not update
        any expression referencing them. The expressions that have been defined
        using these extra expressions will keep using the value of the extra expression
        at the time when the expression was created.
        Thus, it might be best to avoid using extra expressions if you are intending
        to use the gurobipy solver.

        Args:
            problem (Problem): problem from which the extract the extra function expressions.

        Returns:
            GurobipyModel: the GurobipyModel with the expressions added as attributes.
        """
        extra_functions: dict[
            str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float
        ] = {}

        for extra in problem.extra_funcs:
            extra_functions[extra.symbol] = self.parse(extra.func, callback=self.get_expression_by_name)

        return extra_functions

    def init_objectives(
        self, problem: Problem
    ) -> dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr]:
        """Add objective function expressions to a Gurobipy Model.

        Does not yet add any actual gurobipy optimization objectives, only creates a dict containing the
        expressions of the objectives. The objective expressions are stored in the
        evaluator and appropiate gurobipy objective must be added to the model before solving.

        Args:
            problem (Problem): problem from which to extract the objective function expresions.

        Returns:
            dict: dict containing the objective functions.
        """
        objective_functions: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr] = {}
        for obj in problem.objectives:
            gp_expr = self.parse(obj.func, callback=self.get_expression_by_name)
            if isinstance(gp_expr, int | float):
                warnings.warn(
                    "One or more of the problem objectives seems to be a constant.",
                    GurobipyEvaluatorWarning,
                    stacklevel=2,
                )
            if isinstance(gp_expr, gp.GenExpr):
                msg = f"Gurobi does not support objective functions that are not linear or quadratic {gp_expr}"
                raise GurobipyEvaluatorError(msg)

            objective_functions[obj.symbol] = gp_expr

            # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
            objective_functions[f"{obj.symbol}_min"] = -gp_expr if obj.maximize else gp_expr

        return objective_functions

    def init_constraints(self, problem: Problem) -> gp.Model:
        """Add constraint expressions to a Gurobipy Model.

        Args:
            problem (Problem): the problem from which to extract the constraint function expressions.
            model (GurobipyModel): the GurobipyModel to add the exprssions to.

        Raises:
            GurobipyEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            GurobipyModel: the GurobipyModel with the constraint expressions added.
        """
        for cons in problem.constraints:
            gp_expr = self.parse(cons.func, callback=self.get_expression_by_name)

            match con_type := cons.cons_type:
                case ConstraintTypeEnum.LTE:
                    # constraints in DESDEO are defined such that they must be less than zero
                    gp_expr = _le(gp_expr, 0)
                case ConstraintTypeEnum.EQ:
                    gp_expr = _eq(gp_expr, 0)
                case _:
                    msg = f"Constraint type of {con_type} not supported. Must be one of {ConstraintTypeEnum}."
                    raise GurobipyEvaluatorError(msg)

            self.model.addConstr(gp_expr, name=cons.symbol)

        self.model.update()
        return self.model

    def init_scalarizations(
        self, problem: Problem
    ) -> dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr]:
        """Add scalrization expressions to a gurobipy model.

        Scalarizations work identically to objectives, except they are stored in a different
        dict in the GurobipyModel. If you want to solve the problem using a scalarization, the
        evaluator needs to set it as an optimization target first.

        Args:
            problem (Problem): the problem from which to extract the scalarization function expressions.

        Returns:
            dict: the dict with the scalarization expressions. Scalarization functions are always minimized.
        """
        scalarizations: dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr] = {}

        for scal in problem.scalarization_funcs:
            scalarizations[scal.symbol] = self.parse(scal.func, self.get_expression_by_name)

        return scalarizations

    def add_constraint(self, constraint: Constraint) -> gp.Constr:
        """Add a constraint expression to a GurobipyModel.

        If adding a lot of constraints, this function may end up being very slow compared
        to adding the constraints to the stored model directly, because of the model.update() calls.

        Args:
            constraint (Constraint): the constraint function expression.

        Raises:
            GurobipyEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            gurobipy.Constr: The gurobipy constraint that was added.
        """
        gp_expr = self.parse(constraint.func, self.get_expression_by_name)

        match con_type := constraint.cons_type:
            case ConstraintTypeEnum.LTE:
                # constraints in DESDEO are defined such that they must be less than zero
                gp_expr = _le(gp_expr, 0)
            case ConstraintTypeEnum.EQ:
                gp_expr = _eq(gp_expr, 0)
            case _:
                msg = f"Constraint type of {con_type} not supported. Must be one of {ConstraintTypeEnum}."
                raise GurobipyEvaluatorError(msg)

        return_cons = self.model.addConstr(gp_expr, name=constraint.symbol)
        self.model.update()
        return return_cons

    def add_objective(self, obj: Objective):
        """Adds an objective function expression to a GurobipyModel.

        Does not yet add any actual gurobipy optimization objectives, only adds them to the dict
        containing the expressions of the objectives. The objective expressions are stored in the
        GurobipyModel and the evaluator must add the appropiate gurobipy objective before solving.

        Args:
            obj (Objective): the objective function expression to be added.
        """
        gp_expr = self.parse(obj.func, self.get_expression_by_name)
        if isinstance(gp_expr, int | float):
            warnings.warn(
                "One or more of the problem objectives seems to be a constant.", GurobipyEvaluatorWarning, stacklevel=2
            )
        if isinstance(gp.GenExpr, int):
            msg = f"Gurobi does not support objective functions that are not linear or quadratic {gp_expr}"
            raise GurobipyEvaluatorError(msg)

        self.objective_functions[obj.symbol] = gp_expr

        # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
        self.objective_functions[f"{obj.symbol}_min"] = -gp_expr if obj.maximize else gp_expr

    def add_scalarization_function(self, scal: ScalarizationFunction):
        """Adds a scalrization expression to a gurobipy model.

        Scalarizations work identically to objectives, except they are stored in a different
        dict in the GurobipyModel. If you want to solve the problem using a scalarization, the
        evaluator needs to set it as an optimization target first.

        Args:
            scal (ScalarizationFunction): The scalarization function to be added.
        """
        self.scalarizations[scal.symbol] = self.parse(scal.func, self.get_expression_by_name)

    def add_variable(self, var: Variable | TensorVariable) -> gp.Var | gp.MVar:
        """Add variables to the GurobipyModel.

        If adding a lot of variables, this function may end up being very slow compared
        to adding the variables to the stored model directly, because of the model.update() calls.

        Args:
            var (Variable): The definition of the variable to be added.

        Raises:
            GurobipyEvaluatorError: when a problem in extracting the variables is encountered.
                I.e., the variables are of a non supported type.

        Returns:
            gp.Var: the variable that was added to the model.
        """
        if isinstance(var, Variable):
            # handle regular variables
            lowerbound = var.lowerbound if var.lowerbound is not None else float("-inf")
            upperbound = var.upperbound if var.upperbound is not None else float("inf")

            # figure out the variable type
            match var.variable_type:
                case VariableTypeEnum.integer:
                    # variable is integer
                    domain = gp.GRB.INTEGER
                case VariableTypeEnum.real:
                    # variable is real
                    domain = gp.GRB.CONTINUOUS
                case VariableTypeEnum.binary:
                    domain = gp.GRB.BINARY
                case _:
                    msg = f"Could not figure out the type for variable {var}."
                    raise GurobipyEvaluatorError(msg)

            # add the variable to the model
            gvar = self.model.addVar(lb=lowerbound, ub=upperbound, vtype=domain, name=var.symbol)
            # set the initial value, if one has been defined
            if var.initial_value is not None:
                gvar.setAttr("Start", var.initial_value)
        elif isinstance(var, TensorVariable):
            # handle tensor variables, i.e., vectors etc..
            lowerbounds = var.get_lowerbound_values() if var.lowerbounds is not None else np.full(var.shape, float("-inf")).tolist()
            upperbounds = var.get_upperbound_values() if var.upperbounds is not None else np.full(var.shape, float("inf")).tolist()

            # figure out the variable type
            match var.variable_type:
                case VariableTypeEnum.integer:
                    # variable is integer
                    domain = gp.GRB.INTEGER
                case VariableTypeEnum.real:
                    # variable is real
                    domain = gp.GRB.CONTINUOUS
                case VariableTypeEnum.binary:
                    domain = gp.GRB.BINARY
                case _:
                    msg = f"Could not figure out the type for variable {var}."
                    raise GurobipyEvaluatorError(msg)

            # add the variable to the model
            gvar = self.model.addMVar(shape=tuple(var.shape), lb=np.array(lowerbounds), ub=np.array(upperbounds), vtype=domain, name=var.symbol)
            # set the initial value, if one has been defined
            if var.initial_values is not None:
                gvar.setAttr("Start", np.array(var.get_initial_values()))
            self.mvars[var.symbol] = gvar

        self.model.update()
        return gvar

    def get_expression_by_name(
        self, name: str
    ) -> gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr | gp.GenExpr | int | float:
        """Returns a gurobipy expression corresponding to the name.

        Only looks for variables, objective functions, scalarizations, extra functions, and constants.
        This will not find constraints.

        Args:
            name (str): The symbol of the expression.

        Returns:
            gurobipy expression: A mathematical expression that gp.Model can use either as a constraint or an objective
        """
        expression = self.model.getVarByName(name)
        if expression is None:
            # check if an MVar by checking gurobi.MVars stored in the evaluator directly,
            # which results in terms multiplied by zero being removed from the equations:
            if name in self.mvars:
                expression = self.mvars[name]
            elif name in self.objective_functions:
                expression = self.objective_functions[name]
            elif name in self.scalarizations:
                expression = self.scalarizations[name]
            elif name in self.extra_functions:
                expression = self.extra_functions[name]
            elif name in self.constants:
                expression = self.constants[name]
        return expression


    def get_values(self) -> dict[str, float | int | bool | list[float] | list[int]]:   # noqa: C901
        """Get the values from the Gurobipy Model in a dict.

        The keys of the dict will be the symbols defined in the problem utilized to initialize the evaluator.

        Returns:
            dict[str, float | int | bool]: a dict with keys equivalent to the symbols defined in self.problem.
        """
        result_dict = {}

        for var in self.problem.variables:
            # if var is type MVar, get the values of MVar
            if var.symbol in self.mvars:
                result_dict[var.symbol] = self.mvars[var.symbol].getAttr(gp.GRB.Attr.X)
            else:
                result_dict[var.symbol] = self.model.getVarByName(var.symbol).getAttr(gp.GRB.Attr.X)

        for obj in self.problem.objectives:
            result_dict[obj.symbol] = self.objective_functions[obj.symbol].getValue()

        if self.problem.constants is not None:
            for con in self.problem.constants:
                result_dict[con.symbol] = self.constants[con.symbol]

        if self.problem.extra_funcs is not None:
            for extra in self.problem.extra_funcs:
                result_dict[extra.symbol] = self.extra_functions[extra.symbol].getValue()

        if self.problem.constraints is not None:
            for const in self.problem.constraints:
                result_dict[const.symbol] = -self.model.getConstrByName(const.symbol).getAttr("Slack")

        if self.problem.scalarization_funcs is not None:
            for scal in self.problem.scalarization_funcs:
                result_dict[scal.symbol] = self.scalarizations[scal.symbol].getValue()

        return result_dict

    def remove_constraint(self, symbol: str):
        """Removes a constraint from the model.

        If removing a lot of constraints or dealing with a very large model this function
        may be slow because of the model.update() calls. Accessing the stored model directly
        may be faster.

        Args:
            symbol (str): a str representing the symbol of the constraint to be removed.
        """
        self.model.remove(self.model.getConstrByName(symbol))
        self.model.update()

    def remove_variable(self, symbol: str):
        """Removes a variable from the model.

        If removing a lot of variables or dealing with a very large model this function
        may be slow because of the model.update() calls. Accessing the stored model directly
        may be faster.

        Args:
            symbol (str): a str representing the symbol of the variable to be removed.
        """
        if symbol in self.mvars:
            self.model.remove(self.mvars[symbol])
            self.mvars.pop(symbol)
        else:
            self.model.remove(self.model.getVarByName(symbol))
        self.model.update()

    def set_optimization_target(self, target: str, maximize: bool = False):  # noqa: FBT001, FBT002
        """Sets a minimization objective to match the target objective or scalarization of the gurobipy model.

        Args:
            target (str): an str representing a symbol. Needs to match an objective function or scaralization
            function already found in the model.
            maximize (bool): If true, the target function is maximized instead of minimized

        Raises:
            GurobipyEvaluatorError: the given target was not an attribute of the gurobipy model.
        """
        if not ((target in self.objective_functions) or (target in self.scalarizations)):
            msg = f"The gurobipy model has no objective or scalarization named {target}."
            raise GurobipyEvaluatorError(msg)

        obj_expr = self.get_expression_by_name(target)

        if maximize:
            self.model.setObjective(obj_expr, sense=gp.GRB.MAXIMIZE)
        else:
            self.model.setObjective(obj_expr)
