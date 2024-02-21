"""Defines an evaluator compatible with the Problem JSON format and transforms it into a Pyomo model."""
from pyomo.environ import (
    ConcreteModel,
    Expression,
    Var,
    Integers,
    NegativeIntegers,
    NonNegativeIntegers,
    Reals,
    NegativeReals,
    NonNegativeReals,
    Param,
)

from desdeo.problem import Problem, VariableTypeEnum


class PyomoEvaluatorError(Exception):
    """Raised when an error within the PyomoEvaluator class is encountered."""


class PyomoEvaluator:
    """Defines as evaluator that transforms an instance of Problem into a pyomo model."""

    def __init__(self, problem: Problem):
        """Summary."""
        model = ConcreteModel()

        # Add variables
        model = self.init_variables(problem, model)
        # Add constants
        model = self.init_constants(problem, model)
        # Add extra expressions
        if problem.extra_funcs is not None:
            model = self.init_extras(problem, model)

        self.model = model

    def init_variables(self, problem, model):
        """Add variables to the pyomo model.

        Args:
            problem (Problem): problem from which to extract the variables.

        Raises:
            PyomoEvaluator: when a problem in extracting the variables is encountered.
                I.e., the bounds of the variables are incorrect or of a non supported type.
        """
        for var in problem.variables:
            # figure out the variable type
            match (var.lowerbound >= 0, var.upperbound >= 0, var.variable_type):
                case (True, True, VariableTypeEnum.integer):
                    # variable is positive integer
                    domain = NonNegativeIntegers
                case (False, False, VariableTypeEnum.integer):
                    # variable is negative integer
                    domain = NegativeIntegers
                case (False, True, VariableTypeEnum.integer):
                    # variable can be both negative an positive integer
                    domain = Integers
                case (True, False, VariableTypeEnum.integer):
                    # error! lower bound is greater than upper bound
                    msg = (
                        f"The lower bound {var.lowerbound} for variable {var.symbol} is greater than the "
                        f"upper bound {var.upperbound}"
                    )
                    raise PyomoEvaluatorError(msg)
                case (True, True, VariableTypeEnum.real):
                    # variable is positive real
                    domain = NonNegativeReals
                case (False, False, VariableTypeEnum.real):
                    # variable is negative real
                    domain = NegativeReals
                case (False, True):
                    # variable can be both negative and positive real
                    domain = Reals
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
                Var(
                    name=var.name, bounds=(var.lowerbound, var.upperbound), initialize=var.initial_value, domain=domain
                ),
            )

        return model

    def init_constants(self, problem: Problem, model):
        """Add constants to the pyomo model.

        Args:
            problem (Problem): problem from which to extract the constants.

        Raises:
            PyomoEvaluatorError: when the domain of a constant cannot be figure out.
        """
        for con in problem.constants:
            # figure out the domain of the constant
            match (isinstance(con.value, int), isinstance(con.value, float), con.value >= 0):
                case (True, False, True):
                    # positive integer
                    domain = NonNegativeIntegers
                case (True, False, False):
                    # negative integer
                    domain = NegativeIntegers
                case (False, True, True):
                    # positive real
                    domain = NonNegativeReals
                case (False, True, False):
                    # negative real
                    domain = NegativeReals
                case _:
                    # not possible, something went wrong
                    msg = f"Failed to figure out the domain for the constant {con.symbol}."
                    raise PyomoEvaluatorError(msg)

            setattr(model, con.symbol, Param(name=con.name, initialize=con.value, domain=domain))

        return model

    def init_extras(self, problem: Problem, model):
        """Add extra function expressions to the pyomo model.

        Args:
            problem (Problem): problem from which the extract the extra function expressions.
        """
        for extra in problem.extra_funcs:
            # to be done
            expr_str = "model.x_1 + model.x_2"  # TODO! produced by parser when extra expr is parsed

            setattr(model, extra.symbol, eval(expr_str))  # TODO: make this safer! maybe use getattr

        return model
