"""Defines an evaluator compatible with the Problem JSON format and transforms it into a Pyomo model."""

from operator import eq as _eq
from operator import le as _le

import pyomo.environ as pyomo

from desdeo.problem.json_parser import FormatEnum, MathParser
from desdeo.problem.schema import (
    Constant,
    ConstraintTypeEnum,
    Problem,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)


class PyomoEvaluatorError(Exception):
    """Raised when an error within the PyomoEvaluator class is encountered."""


class PyomoEvaluator:
    """Defines an evaluator that transforms an instance of Problem into a pyomo model."""

    def __init__(self, problem: Problem):
        """Initializes the evaluator.

        Args:
            problem (Problem): the problem to be transformed in a pyomo model.
        """
        model = pyomo.ConcreteModel()

        # set the parser
        self.parse = MathParser(to_format=FormatEnum.pyomo).parse

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

    @classmethod
    def _bounds_rule(cls, lowerbounds, upperbounds):
        def bounds_rule(model, *args) -> tuple:
            indices = tuple(arg - 1 for arg in args)

            lower_value = lowerbounds
            upper_value = upperbounds

            for index in indices:
                lower_value = lower_value[index]
                upper_value = upper_value[index]

            return (lower_value, upper_value)

        return bounds_rule

    @classmethod
    def _init_rule(cls, initial_values):
        def init_rule(model, *args):
            indices = tuple(arg - 1 for arg in args)

            initial_value = initial_values

            for index in indices:
                initial_value = initial_value[index]

            return initial_value

        return init_rule

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
            if isinstance(var, Variable):
                # handle regular variables
                lowerbound = var.lowerbound if var.lowerbound is not None else float("-inf")
                upperbound = var.upperbound if var.upperbound is not None else float("inf")

                # figure out the variable type
                match (lowerbound >= 0, upperbound >= 0, var.variable_type):
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
                    case (False, True, VariableTypeEnum.real):
                        # variable can be both negative and positive real
                        domain = pyomo.Reals
                    case (True, False, VariableTypeEnum.real):
                        # error! lower bound is greater than upper bound
                        msg = (
                            f"The lower bound {var.lowerbound} for variable {var.symbol} is greater than the "
                            f"upper bound {var.upperbound}"
                        )
                        raise PyomoEvaluatorError(msg)
                    # TODO: check binary type!
                    case _:
                        msg = f"Could not figure out the type for variable {var}."
                        raise PyomoEvaluatorError(msg)

                # if a variable's initial value is set, use it. Otherwise, check if the lower and upper bounds
                # are defined, if they are, use the mid-point of the bounds, otherwise use the initial value, which is
                # None.
                if var.initial_value is not None:
                    initial_value = var.initial_value
                else:
                    initial_value = (
                        var.initial_value
                        if var.lowerbound is None and var.upperbound is None
                        else (var.lowerbound + var.upperbound) / 2
                    )

                pyomo_var = pyomo.Var(
                    name=var.name, initialize=initial_value, bounds=(var.lowerbound, var.upperbound), domain=domain
                )

            elif isinstance(var, TensorVariable):
                # handle tensor variables, i.e., vectors etc..
                # create the needed range sets
                index_sets = [pyomo.RangeSet(1, dim_size) for dim_size in var.shape]

                # TODO: check domain properly
                if var.variable_type == VariableTypeEnum.binary:
                    domain = pyomo.Binary
                elif var.variable_type == VariableTypeEnum.integer:
                    domain = pyomo.Integers
                else:
                    domain = pyomo.Reals

                # create the Var
                pyomo_var = pyomo.Var(
                    *index_sets,
                    name=var.name,
                    initialize=self._init_rule(var.get_initial_values()),
                    bounds=self._bounds_rule(var.get_lowerbound_values(), var.get_upperbound_values()),
                    domain=domain,
                )

            else:
                msg = f"Unsupported variable type '{type(var)} encountered."
                raise PyomoEvaluatorError(msg)

            # add and then construct the variable
            setattr(model, var.symbol, pyomo_var)
            getattr(model, var.symbol).construct()

        return model

    def init_constants(self, problem: Problem, model: pyomo.Model) -> pyomo.Model:
        """Add constants to a pyomo model.

        Args:
            problem (Problem): problem from which to extract the constants.
            model (pyomo.Model): the pyomo model to add the constants to.

        Raises:
            PyomoEvaluatorError: when the domain of a constant cannot be figured out.

        Returns:
            pyomo.Model: the pyomo model with the constants added as attributes.
        """
        for con in problem.constants:
            # Handle regular constnants
            if isinstance(con, Constant):
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

                pyomo_param = pyomo.Param(name=con.name, default=con.value, domain=domain)

            elif isinstance(con, TensorConstant):
                # handle TensorConstants, like vectors
                # create the needed range sets
                index_sets = [pyomo.RangeSet(1, dim_size) for dim_size in con.shape]

                # TODO: check domain properly
                # for now, constants are always assumed to be real (which is quite safe to do...)
                domain = pyomo.Reals

                # create the Con
                pyomo_param = pyomo.Param(
                    *index_sets,
                    name=con.name,
                    initialize=self._init_rule(con.get_values()),
                    domain=domain,
                )
            else:
                msg = f"Unsupported constant type '{type(con)}' encountered."
                raise PyomoEvaluatorError(msg)

            setattr(model, con.symbol, pyomo_param)

        return model

    def init_extras(self, problem: Problem, model: pyomo.Model) -> pyomo.Model:
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

        Does not yet add any actual pyomo objectives, only the expressions of the objectives.
        A pyomo solved must add the appropiate pyomo objective before solving.

        Args:
            problem (Problem): problem from which to extract the objective function expresions.
            model (pyomo.Model): the pyomo model to add the expressions to.

        Returns:
            pyomo.Model: the pyomo model with the objective expressions added as pyomo Objectives.
                The objectives are deactivated by default.
        """
        for obj in problem.objectives:
            pyomo_expr = self.parse(obj.func, model)

            setattr(model, obj.symbol, pyomo_expr)

            # the obj.symbol_min objectives are used when optimizing and building scalarizations etc...
            setattr(model, f"{obj.symbol}_min", -pyomo_expr if obj.maximize else pyomo_expr)

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
        for scal in problem.scalarization_funcs:
            pyomo_expr = self.parse(scal.func, model)

            setattr(model, scal.symbol, pyomo_expr)

        return model

    def evaluate(self, xs: dict[str, float | int | bool]) -> pyomo.Model:
        """Evaluate the current pyomo model with the given decision variable values.

        Warning:
            This should not be used for actually solving the pyomo model! For debugging mostly.

        Args:
            xs (dict[str, list[float | int | bool]]): a dict with the decision variable symbols
                as the keys followed by the corresponding decision variable values. The symbols
                must match the symbols defined for the decision variables defined in the `Problem` being solved.
                Each list in the dict should contain the same number of values.

        Returns:
            pyomo.Model: the pyomo model with its variable values set to the values found in xs.
        """
        for var in self.problem.variables:
            setattr(self.model, var.symbol, xs[var.symbol])

        return self.model

    def get_values(self) -> dict[str, float | int | bool]:  # noqa: C901
        """Get the values from the pyomo model in dict.

        The keys of the dict will be the symbols defined in the problem utilized to initialize the evaluator.

        Returns:
            dict[str, float | int | bool]: a dict with keys equivalent to the symbols defined in self.problem.
        """
        result_dict = {}

        for var in self.problem.variables:
            if isinstance(var, Variable):
                result_dict[var.symbol] = pyomo.value(getattr(self.model, var.symbol))
            elif isinstance(var, TensorVariable):
                result_dict[var.symbol] = getattr(self.model, var.symbol).get_values()
            else:
                msg = f"Unsupported variable type {type(var)} encountered."
                raise PyomoEvaluatorError(msg)

        for obj in self.problem.objectives:
            result_dict[obj.symbol] = pyomo.value(getattr(self.model, obj.symbol))

        if self.problem.constants is not None:
            for con in self.problem.constants:
                if isinstance(con, Constant):
                    result_dict[con.symbol] = pyomo.value(getattr(self.model, con.symbol))
                elif isinstance(con, TensorConstant):
                    result_dict[con.symbol] = getattr(self.model, con.symbol).extract_values()
                else:
                    msg = f"Unsupported variable type {type(var)} encountered."
                    raise PyomoEvaluatorError(msg)

        if self.problem.extra_funcs is not None:
            for extra in self.problem.extra_funcs:
                result_dict[extra.symbol] = pyomo.value(getattr(self.model, extra.symbol))

        if self.problem.constraints is not None:
            for const in self.problem.constraints:
                result_dict[const.symbol] = pyomo.value(getattr(self.model, const.symbol))

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
