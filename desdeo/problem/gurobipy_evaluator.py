"""Defines an evaluator compatible with the Problem JSON format and transforms it into a GurobipyModel."""

from operator import eq as _eq
from operator import le as _le

import gurobipy as gp
from gurobipy_model_extension import GurobipyModel

import warnings

from desdeo.problem.json_parser import FormatEnum, MathParser
from desdeo.problem.schema import (
    Constraint, 
    ConstraintTypeEnum, 
    Objective, 
    Problem, 
    ScalarizationFunction, 
    Variable, 
    VariableTypeEnum
)


class GurobipyEvaluatorError(Exception):
    """Raised when an error within the GurobipyEvaluator class is encountered."""

class GurobipyEvaluatorWarning(UserWarning):
    """Raised when the problem contains features that are poorly supported in gurobipy."""

class GurobipyEvaluator:
    """Defines as evaluator that transforms an instance of Problem into a GurobipyModel."""

    def __init__(self, problem: Problem):
        """Initialized the evaluator.

        Args:
            problem (Problem): the problem to be transformed in a GurobipyModel.
        """
        model = GurobipyModel(problem.name)

        # set the parser
        self.parse = MathParser(to_format=FormatEnum.gurobipy).parse

        # Add variables
        model = self.init_variables(problem, model)

        # Add constants, if any
        if problem.constants is not None:
            model = self.init_constants(problem, model)

        # Add extra expressions, if any
        if problem.extra_funcs is not None:
            model = self.init_extras(problem, model)

        # Add objective function expressions
        model = self.init_objectives(problem, model)

        # Add constraints, if any
        if problem.constraints is not None:
            model = self.init_constraints(problem, model)

        # Add scalarization functions, if any
        if problem.scalarization_funcs is not None:
            model = self.init_scalarizations(problem, model)

        self.model = model
        self.problem = problem

    def init_variables(self, problem: Problem, model: GurobipyModel) -> GurobipyModel:
        """Add variables to the GurobipyModel.

        Args:
            problem (Problem): problem from which to extract the variables.
            model (GurobipyModel): the GurobipyModel to add the variables to.

        Raises:
            GurobipyEvaluatorError: when a problem in extracting the variables is encountered.
                I.e., the variables are of a non supported type.

        Returns:
            GurobipyModel: the GurobipyModel with the variables added as attributes.
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

        #update the model before returning, so that other expressions can reference the variables
        model.update()

        return model

    def init_constants(self, problem: Problem, model: GurobipyModel) -> GurobipyModel:
        """Add constants to a GurobipyModel. 
        
        Gurobi does not really have constants, so this function instead  
        stores them in the GurobipyModel object. 
        This is necessary to get the MathParser to understand the constants
        used in the problem, but updating them at a later point will not update
        any expression referencing them. The expressions that have been defined
        using these constants will keep using the numeric value of the constant
        at the time when the expression was created.
        Thus, it might be best to avoid using constants if you are intending
        to use the gurobipy solver. 

        Args:
            problem (Problem): problem from which to extract the constants.
            model (GurobipyModel): the GurobipyModel to add the constants to.

        Raises:
            GurobipyEvaluatorError: when the domain of a constant cannot be figured out.

        Returns:
            GurobipyModel: the GurobipyModel with the constants added as variables.
        """
        for con in problem.constants:
            model.addConstant(con.value,name=con.symbol)

        return model

    def init_extras(self, problem: Problem, model: GurobipyModel) -> GurobipyModel:
        """Add extra function expressions to a GurobipyModel. 
        
        Gurobi does not support extra expressions natively, so this function instead  
        stores them in the GurobipyModel object. 
        This is necessary to get the MathParser to understand the extra expressions
        used in the problem, but updating them at a later point will not update
        any expression referencing them. The expressions that have been defined
        using these extra expressions will keep using the value of the extra expression
        at the time when the expression was created.
        Thus, it might be best to avoid using extra expressions if you are intending
        to use the gurobipy solver. 

        Args:
            problem (Problem): problem from which the extract the extra function expressions.
            model (GurobipyModel): the GurobipyModel to add the extra function expressions to.

        Returns:
            GurobipyModel: the GurobipyModel with the expressions added as attributes.
        """
        for extra in problem.extra_funcs:
            model.addExtraFunction(self.parse(extra.func, model), name=extra.symbol)

        return model

    def init_objectives(self, problem: Problem, model: GurobipyModel) -> GurobipyModel:
        """Add objective function expressions to a GurobipyModel.

        Does not yet add any actual gurobipy optimization objectives, only creates a dict containing the 
        expressions of the objectives. The objective expressions are stored in the 
        GurobipyModel and the evaluator must add the appropiate gurobipy objective before solving.

        Args:
            problem (Problem): problem from which to extract the objective function expresions.
            model (GurobipyModel): the GurobipyModel containing the variables that the expressions reference.

        Returns:
            GurobipyModel: the GurobipyModel with the objectives added.
        """
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

            model.addObjectiveFunction(gp_expr,name=obj.symbol)

            # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
            model.addObjectiveFunction((-gp_expr if obj.maximize else gp_expr),name=f"{obj.symbol}_min")

        return model

    def init_constraints(self, problem: Problem, model: GurobipyModel) -> GurobipyModel:
        """Add constraint expressions to a GurobipyModel.

        Args:
            problem (Problem): the problem from which to extract the constraint function expressions.
            model (GurobipyModel): the GurobipyModel to add the exprssions to.

        Raises:
            GurobipyEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            GurobipyModel: the GurobipyModel with the constraint expressions added.
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

        model.update()
        return model

    def init_scalarizations(self, problem: Problem, model: GurobipyModel) -> GurobipyModel:
        """Add scalrization expressions to a gurobipy model.

        Scalarizations work identically to objectives, except they are stored in a different
        dict in the GurobipyModel. If you want to solve the problem using a scalarization, the
        evaluator needs to set it as an optimization target first.

        Args:
            problem (Problem): the problem from which to extract the scalarization function expressions.
            model (GurobipyModel): the GurobipyModel to add the expressions to.

        Returns:
            GurobipyModel: the GurobipyModel with the scalarization expressions. Scalarization functions are always minimized.
        """
        for scal in problem.scalarization_funcs:
            model.addScalarization(self.parse(scal.func, model),scal.symbol)

        return model
    
    def addConstraint(self, constraint: Constraint) -> gp.Constr:
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
        gp_expr = self.parse(constraint.func, self.model)

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
        
    def addObjective(self, obj: Objective):
        """Adds an objective function expression to a GurobipyModel.

        Does not yet add any actual gurobipy optimization objectives, only adds them to the dict 
        containing the expressions of the objectives. The objective expressions are stored in the 
        GurobipyModel and the evaluator must add the appropiate gurobipy objective before solving.

        Args:
            obj (Objective): the objective function expression to be added.
        """
        gp_expr = self.parse(obj.func, self.model)
        if isinstance(gp_expr, int) or isinstance(gp_expr, float):
            warnings.warn(
                "One or more of the problem objectives seems to be a constant.",
                GurobipyEvaluatorWarning
            )
        if isinstance(gp.GenExpr, int):
            msg = f"Gurobi does not support objective functions that are not linear or quadratic {gp_expr}"
            raise GurobipyEvaluatorError(msg)

        self.model.addObjectiveFunction(gp_expr,name=obj.symbol)

        # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
        self.model.addObjectiveFunction((-gp_expr if obj.maximize else gp_expr),name=f"{obj.symbol}_min")

    def addScalarizationFunction(self, scal: ScalarizationFunction):
        """Adds a scalrization expression to a gurobipy model.

        Scalarizations work identically to objectives, except they are stored in a different
        dict in the GurobipyModel. If you want to solve the problem using a scalarization, the
        evaluator needs to set it as an optimization target first.

        Args:
            scal (ScalarizationFunction): The scalarization function to be added.
        """
        self.model.addScalarization(self.parse(scal.func, self.model),scal.symbol)

    def addVariable(self, var: Variable) -> gp.Var:
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
        gvar = self.model.addVar(lb=lowerbound, ub=upperbound, vtype=domain, name=var.symbol)
        # set the initial value, if one has been defined
        if var.initial_value is not None:
            gvar.setAttr("Start", var.initial_value)
        
        self.model.update()
        return gvar

    def get_values(self) -> dict[str, float | int | bool]:
        """Get the values from the GurobipyModel in a dict.

        The keys of the dict will be the symbols defined in the problem utilized to initialize the evaluator.

        Returns:
            dict[str, float | int | bool]: a dict with keys equivalent to the symbols defined in self.problem.
        """
        result_dict = {}

        for var in self.problem.variables:
            result_dict[var.symbol] = self.model.getVarByName(var.symbol).getAttr(gp.GRB.Attr.X)

        for obj in self.problem.objectives:
            result_dict[obj.symbol] = self.model.objectiveFunctions[obj.symbol].getValue()

        if self.problem.constants is not None:
            for con in self.problem.constants:
                result_dict[con.symbol] = self.model.constants[con.symbol]

        if self.problem.extra_funcs is not None:
            for extra in self.problem.extra_funcs:
                result_dict[extra.symbol] = self.model.extraFunctions[extra.symbol].getValue()

        if self.problem.constraints is not None:
            for const in self.problem.constraints:
                result_dict[const.symbol] = -self.model.getConstrByName(const.symbol).getAttr("Slack")

        if self.problem.scalarization_funcs is not None:
            for scal in self.problem.scalarization_funcs:
                result_dict[scal.symbol] = self.model.scalarizations[scal.symbol]

        return result_dict
    
    def removeConstraint(self, symbol: str):
        """Removes a constraint from the model.

        If removing a lot of constraints or dealing with a very large model this function 
        may be slow because of the model.update() calls. Accessing the stored model directly
        may be faster.
        
        Args:
            symbol (str): a str representing the symbol of the constraint to be removed.
        """
        self.model.remove(self.model.getConstrByName(symbol))
        self.model.update()

    def removeVariable(self, symbol: str):
        """Removes a variable from the model.

        If removing a lot of variables or dealing with a very large model this function 
        may be slow because of the model.update() calls. Accessing the stored model directly
        may be faster.
        
        Args:
            symbol (str): a str representing the symbol of the variable to be removed.
        """
        self.model.remove(self.model.getVarByName(symbol))
        self.model.update()

    def set_optimization_target(self, target: str):
        """Sets a minimization objective to match the target objective or scalarization of the gurobipy model.

        Args:
            target (str): an str representing a symbol. Needs to match an objective function or scaralization
            function already found in the model.

        Raises:
            GurobipyEvaluatorError: the given target was not an attribute of the gurobipy model.
        """
        if not ((target in self.model.objectiveFunctions) or (target in self.model.scalarizations)):
            msg = f"The gurobipy model has no objective or scalarization named {target}."
            raise GurobipyEvaluatorError(msg)

        obj_expr = self.model.getExpressionByName(target)

        self.model.setObjective(obj_expr)

