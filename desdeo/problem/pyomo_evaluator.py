"""Defines an evaluator compatible with the Problem JSON format and transforms it into a Pyomo model."""
from operator import le as _le
from operator import eq as _eq

import pyomo.environ as pyomo

from desdeo.problem import ConstraintTypeEnum, Problem, VariableTypeEnum, FormatEnum, MathParser


class PyomoEvaluatorError(Exception):
    """Raised when an error within the PyomoEvaluator class is encountered."""


class PyomoEvaluator:
    """Defines as evaluator that transforms an instance of Problem into a pyomo model."""

    def __init__(self, problem: Problem):
        """Summary."""
        model = pyomo.ConcreteModel()

        # set the parser
        self.parse = MathParser(to_format=FormatEnum.pyomo).parse

        # Add variables
        model = self.init_variables(problem, model)

        # Add constants
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
        if problem.scalarizations_funcs is not None:
            model = self.init_scalarizations(problem, model)

        self.model = model

    def init_variables(self, problem: Problem, model: pyomo.Model) -> pyomo.Model:
        """Add variables to the pyomo model.

        Args:
            problem (Problem): problem from which to extract the variables.
            model (pyomo.Model): the pyomo model to add the variables to.

        Raises:
            PyomoEvaluator: when a problem in extracting the variables is encountered.
                I.e., the bounds of the variables are incorrect or of a non supported type.

        Returns:
            pyomo.Model: the pyomo model with the variables added as attributes.
        """
        for var in problem.variables:
            # figure out the variable type
            match (var.lowerbound >= 0, var.upperbound >= 0, var.variable_type):
                case (True, True, VariableTypeEnum.integer):
                    # variable is positive integer
                    domain = pyomo.NonNegativeIntegers
                case (False, False, VariableTypeEnum.integer):
                    # variable is negative integer
                    domain = pyomo.NegativeIntegers
                case (False, True, VariableTypeEnum.integer):
                    # variable can be both negative an positive integer
                    domain = pyomo.Integers
                case (True, False, VariableTypeEnum.integer):
                    # error! lower bound is greater than upper bound
                    msg = (
                        f"The lower bound {var.lowerbound} for variable {var.symbol} is greater than the "
                        f"upper bound {var.upperbound}"
                    )
                    raise PyomoEvaluatorError(msg)
                case (True, True, VariableTypeEnum.real):
                    # variable is positive real
                    domain = pyomo.NonNegativeReals
                case (False, False, VariableTypeEnum.real):
                    # variable is negative real
                    domain = pyomo.NegativeReals
                case (False, True):
                    # variable can be both negative and positive real
                    domain = pyomo.Reals
                case (True, False):
                    # eror! lower bound is greater than upper bound
                    msg = (
                        f"The lower bound {var.lowerbound} for variable {var.symbol} is greater than the "
                        f"upper bound {var.upperbound}"
                    )
                    raise PyomoEvaluatorError(msg)
                case _:
                    msg = f"Could not figure out the type for variable {var}."
                    raise PyomoEvaluatorError(msg)

            setattr(
                model,
                var.symbol,
                pyomo.Var(
                    name=var.name, bounds=(var.lowerbound, var.upperbound), initialize=var.initial_value, domain=domain
                ),
            )

        return model

    def init_constants(self, problem: Problem, model: pyomo.Model) -> pyomo.Model:
        """Add constants to a pyomo model.

        Args:
            problem (Problem): problem from which to extract the constants.
            model (pyomo.Model): the pyomo model to add the constants to.

        Raises:
            PyomoEvaluatorError: when the domain of a constant cannot be figure out.

        Returns:
            pyomo.Model: the pyomo model with the constants added as attributes.
        """
        for con in problem.constants:
            # figure out the domain of the constant
            match (isinstance(con.value, int), isinstance(con.value, float), con.value >= 0):
                case (True, False, True):
                    # positive integer
                    domain = pyomo.NonNegativeIntegers
                case (True, False, False):
                    # negative integer
                    domain = pyomo.NegativeIntegers
                case (False, True, True):
                    # positive real
                    domain = pyomo.NonNegativeReals
                case (False, True, False):
                    # negative real
                    domain = pyomo.NegativeReals
                case _:
                    # not possible, something went wrong
                    msg = f"Failed to figure out the domain for the constant {con.symbol}."
                    raise PyomoEvaluatorError(msg)

            setattr(model, con.symbol, pyomo.Param(name=con.name, initialize=con.value, domain=domain))

        return model

    def init_extras(self, problem: Problem, model: pyomo.Model):
        """Add extra function expressions to a pyomo model.

        Args:
            problem (Problem): problem from which the extract the extra function expressions.
            model (pyomo.Model): the pyomo model to add the extra function expressions to.

        Returns:
            pyomo.Model: the pyomo model with the expressions added as attributes.
        """
        for extra in problem.extra_funcs:
            pyomo_expr = self.parse(extra.func, model)

            setattr(model, extra.symbol, pyomo_expr)

        return model

    def init_objectives(self, problem: Problem, model: pyomo.Model) -> pyomo.Model:
        """Add objective function expressions to a pyomo model.

        Args:
            problem (Problem): problem from which to extract the objective function expresions.
            model (pyomo.Model): the pyomo model to add the expressions to.

        Returns:
            pyomo.Model: the pyomo model with the objective expressions added as pyomo Objectives.
                The objectives are deactivated by default.
        """
        for obj in problem.objectives:
            pyomo_expr = self.parse(obj.func, model)

            obj_expr = pyomo.Objective(
                expr=pyomo_expr,
                sense=pyomo.maximize if obj.maximize else pyomo.minimize,
                name=obj.name,
            )
            obj_expr.deactivate()

            setattr(model, obj.symbol, obj_expr)

            obj_min_expr = pyomo.Objective(
                expr=-obj_expr if obj.maximize else obj_expr,
                sense=pyomo.minimize,
                name=obj.name,
            )
            obj_min_expr.deactivate()

            # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
            setattr(model, f"{obj.symbol}_min", obj_min_expr)

        return model

    def init_constraints(self, problem: Problem, model: pyomo.Model) -> pyomo.Model:
        """Add constraint expressions to a pyomo model.

        Args:
            problem (Problem): the problem from which to extract the constraint function expressions.
            model (pyomo.Model): the pyomo model to add the exprssions to.

        Raises:
            PyomoEvaluatorError: when an unsupported constraint type is encountered.

        Returns:
            pyomo.Model: the pyomo model with the constraint expressions added as pyomo Constraints.
        """
        for cons in problem.constraints:
            pyomo_expr = self.parse(cons.func, model)

            match con_type := cons.cons_type:
                case ConstraintTypeEnum.LTE:
                    # constraints in DESDEO are defined such that they must be less than zero
                    pyomo_expr = _le(pyomo_expr, 0)
                case ConstraintTypeEnum.EQ:
                    pyomo_expr = _eq(pyomo_expr, 0)
                case _:
                    msg = f"Constraint type of {con_type} not supported. Must be one of {ConstraintTypeEnum}."
                    raise PyomoEvaluatorError(msg)

            cons_expr = pyomo.Constraint(expr=pyomo_expr, name=cons.name)

            setattr(model, cons.symbol, cons_expr)

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
        for scal in problem.scalarizations_funcs:
            pyomo_expr = self.parse(scal.func, model)

            # scalarization functions are always assumed to be minimized!
            scal_expr = pyomo.Objective(expr=pyomo_expr, name=scal.name, sense=pyomo.minimize)
            scal_expr.deactivate()

            setattr(model, scal.symbol, scal_expr)

        return model
