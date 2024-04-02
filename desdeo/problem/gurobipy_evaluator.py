"""Defines an evaluator compatible with the Problem JSON format and transforms it into a gurobipy model."""

from operator import eq as _eq
from operator import le as _le

import gurobipy as gp

import warnings

from desdeo.problem.json_parser import FormatEnum, MathParser
from desdeo.problem.schema import ConstraintTypeEnum, Problem, VariableTypeEnum


class GurobipyEvaluatorError(Exception):
    """Raised when an error within the GurobipyEvaluator class is encountered."""

class GurobipyEvaluatorWarning(UserWarning):
    """Raised when the problem contains features that are poorly supported in gurobipy."""

class GurobipyEvaluator:
    """Defines as evaluator that transforms an instance of Problem into a gurobipy model."""

    def __init__(self, problem: Problem):
        """Initialized the evaluator.

        Args:
            problem (Problem): the problem to be transformed in a gurobipy model.
        """
        model = gp.Model(problem.name)

        # set the parser
        self.parse = MathParser(to_format=FormatEnum.gurobipy).parse

        # Add variables
        model = self.init_variables(problem, model)

        # Add constants, if any
        if problem.constants is not None:
            warnings.warn(
                "Gurobipy does not really support constants. Adding them as variables.",
                GurobipyEvaluatorWarning
            )
            model = self.init_constants(problem, model)

        # Add extra expressions, if any
        if problem.extra_funcs is not None:
            warnings.warn(
                "Gurobipy does not really support extra expressions. Adding them as variables.",
                GurobipyEvaluatorWarning
            )
            model = self.init_extras(problem, model)

        # Add objective function expressions
        objectives = self.init_objectives(problem, model)

        # Add constraints, if any
        if problem.constraints is not None:
            model = self.init_constraints(problem, model)

        # Add scalarization functions, if any
        if problem.scalarization_funcs is not None:
            model = self.init_scalarizations(problem, model)

        self.model = model
        self.problem = problem
        self.objectives = objectives

    def init_variables(self, problem: Problem, model: gp.Model) -> gp.Model:
        """Add variables to the gurobipy model.

        Args:
            problem (Problem): problem from which to extract the variables.
            model (gp.Model): the gurobipy model to add the variables to.

        Raises:
            GurobipyEvaluatorError: when a problem in extracting the variables is encountered.
                I.e., the variables are of a non supported type.

        Returns:
            gp.Model: the gurobipy model with the variables added as attributes.
        """
        for var in problem.variables:
            lowerbound = var.lowerbound if var.lowerbound is not None else float("-inf")
            upperbound = var.upperbound if var.upperbound is not None else float("inf")

            # figure out the variable type
            match (var.variable_type):
                case (VariableTypeEnum.integer):
                    # variable is integer
                    domain = gp.GRB.INTEGER
                case (VariableTypeEnum.real):
                    # variable is real
                    domain = gp.GRB.CONTINUOUS
                case (VariableTypeEnum.binary):
                    domain = gp.GRB.BINARY
                case _:
                    msg = f"Could not figure out the type for variable {var}."
                    raise GurobipyEvaluatorError(msg)

            # add the variable to the model
            gvar = model.addVar(lb=lowerbound, ub=upperbound, vtype=domain, name=var.symbol)
            # set the initial value, if one has been defined
            if var.initial_value is not None:
                gvar.setAttr("Start", var.initial_value)

        return model

    def init_constants(self, problem: Problem, model: gp.Model) -> gp.Model:
        """Add constants to a gurobipy model. 
        
        Gurobi does not really have constants, so this function instead adds 
        variables whose upper and lower bounds match the constant's value. 
        This is necessary to get the MathParser to understand the constants
        used in the problem, but Gurobi presolve should be able to remove all
        these unnecessary variables when it comes time to solve the problem.
        Still, it might be best to avoid using constants if you are intending
        to use the gurobipy solver. 

        Args:
            problem (Problem): problem from which to extract the constants.
            model (gp.Model): the gurobipy model to add the constants to.

        Raises:
            GurobipyEvaluatorError: when the domain of a constant cannot be figured out.

        Returns:
            gp.Model: the gurobipy model with the constants added as variables.
        """
        for con in problem.constants:
            # figure out the domain of the constant
            match (isinstance(con.value, int), isinstance(con.value, float)):
                case (True, False):
                    # integer
                    domain = gp.GRB.INTEGER
                case (False, True):
                    # real
                    domain = gp.GRB.CONTINUOUS
                case _:
                    # not possible, something went wrong
                    msg = f"Failed to figure out the domain for the constant {con.symbol}."
                    raise GurobipyEvaluatorError(msg)


            # add the variable to the model
            gvar = model.addVar(lb=con.value, ub=con.value, vtype=domain, name=con.symbol)
            # set the initial value
            gvar.setAttr("Start", con.value)

        return model

    def init_extras(self, problem: Problem, model: gp.Model) -> gp.Model:
        """Add extra function expressions to a gurobipy model. Because gurobipy does not
        support extra expressions natively, this function adds the expressions as variables
        and adds a constraint that forces that variable to match the expression.

        Args:
            problem (Problem): problem from which the extract the extra function expressions.
            model (gp.Model): the gurobipy model to add the extra function expressions to.

        Returns:
            gp.Model: the gurobipy model with the expressions added as attributes.
        """
        for extra in problem.extra_funcs:
            gp_expr = self.parse(extra.func, model)
            gp_var = model.addVar(lb=float("-inf"), name=extra.symbol)
            model.addConstr(gp_var == gp_expr)

        return model

    def init_objectives(self, problem: Problem, model: gp.Model) -> (
            dict[str, gp.Var | gp.MVar | gp.LinExpr | gp.QuadExpr | gp.MLinExpr | gp.MQuadExpr]):
        """Add objective function expressions to a gurobipy model.

        Does not yet add any actual gurobipy objectives, only creates a dict containing the 
        expressions of the objectives. The objective expressions are stored in the 
        GurobipyEvaluator and the evaluator must add the appropiate gurobipy objective before solving.

        Args:
            problem (Problem): problem from which to extract the objective function expresions.
            model (gp.Model): the gurobipy model containing the variables that the expressions reference.

        Returns:
            dict: dictionary containing the objectives as gurobipy expressions indexed by objective symbols.
        """
        objectives = dict()
        for obj in problem.objectives:
            gp_expr = self.parse(obj.func, model)
            if isinstance(gp_expr, int) or isinstance(gp_expr, float):
                warnings.warn(
                    "One or more of the problem objectives seems to be a constant.",
                    GurobipyEvaluatorWarning
                )
            if isinstance(gp.GenExpr, int):
                msg = f"Gurobi does not support objective functions that are not linear or quadratic {gp_expr}"
                raise GurobipyEvaluatorError(msg)

            objectives[obj.symbol] = gp_expr

            # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
            objectives[f"{obj.symbol}_min"] = (-gp_expr if obj.maximize else gp_expr)

        return objectives

    def init_constraints(self, problem: Problem, model: gp.Model) -> gp.Model:
        """Add constraint expressions to a gurobipy model.

        Args:
            problem (Problem): the problem from which to extract the constraint function expressions.
            model (gp.Model): the gurobipy model to add the exprssions to.

        Raises:
            GurobipyEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            gp.Model: the gurobipy model with the constraint expressions added.
        """
        for cons in problem.constraints:
            gp_expr = self.parse(cons.func, model)

            match con_type := cons.cons_type:
                case ConstraintTypeEnum.LTE:
                    # constraints in DESDEO are defined such that they must be less than zero
                    gp_expr = _le(gp_expr, 0)
                case ConstraintTypeEnum.EQ:
                    gp_expr = _eq(gp_expr, 0)
                case _:
                    msg = f"Constraint type of {con_type} not supported. Must be one of {ConstraintTypeEnum}."
                    raise GurobipyEvaluatorError(msg)

            model.addConstr(gp_expr, name=cons.symbol)

        return model

    def init_scalarizations(self, problem: Problem, model: pyomo.Model) -> pyomo.Model:
        """Add scalrization expressions to a pyomo model.

        Args:
            problem (Problem): the problem from which to extract thescalarization function expressions.
            model (pyomo.Model): the pyomo model to add the expressions to.

        Returns:
            pyomo.Model: the pyomo model with the scalarization expressions addedd as pyomo Objectives.
                The objectives are deactivated by default. Scalarization functions are always minimized.
        """
        for scal in problem.scalarization_funcs:
            pyomo_expr = self.parse(scal.func, model)

            setattr(model, scal.symbol, pyomo_expr)

        return model

    def get_values(self) -> dict[str, float | int | bool]:
        """Get the values from the gurobipy model in dict.

        The keys of the dict will be the symbols defined in the problem utilized to initialize the evaluator.

        Returns:
            dict[str, float | int | bool]: a dict with keys equivalent to the symbols defined in self.problem.
        """
        result_dict = {}

        for var in self.problem.variables:
            result_dict[var.symbol] = self.model.getVarByName(var.symbol).getAttr(gp.GRB.Attr.X)

        for obj in self.problem.objectives:
            result_dict[obj.symbol] = self.objectives[obj.symbol].getValue()

        if self.problem.constants is not None:
            for con in self.problem.constants:
                result_dict[con.symbol] = self.model.getVarByName(con.symbol).getAttr(gp.GRB.Attr.X)

        if self.problem.extra_funcs is not None:
            for extra in self.problem.extra_funcs:
                result_dict[extra.symbol] = self.model.getVarByName(extra.symbol).getAttr(gp.GRB.Attr.X)

        if self.problem.constraints is not None:
            for const in self.problem.constraints:
                result_dict[const.symbol] = -self.model.getConstrByName(const.symbol).getAttr("Slack")

        if self.problem.scalarization_funcs is not None:
            for scal in self.problem.scalarization_funcs:
                result_dict[scal.symbol] = pyomo.value(getattr(self.model, scal.symbol))

        return result_dict

    def set_optimization_target(self, target: str):
        """Creates a minimization objective from the target attribute of the pyomo model.

        The attribute name of the pyomo objective will be target + _objective, e.g.,
        'f_1' will become 'f_1_objective'. This is done so that the original f_1 expressions
        attribute does not get reassigned.

        Args:
            target (str): an str representing a symbol.

        Raises:
            PyomoEvaluatorError: the given target was not an attribute of the pyomo model.
        """
        if not hasattr(self.model, target):
            msg = f"The pyomo model has no attribute {target}."
            raise PyomoEvaluatorError(msg)

        obj_expr = getattr(self.model, target)

        objective = pyomo.Objective(expr=obj_expr, sense=pyomo.minimize, name=target)

        # add the postfix '_objective' to the attribute name of the pyomo objective
        setattr(self.model, f"{target}_objective", objective)
