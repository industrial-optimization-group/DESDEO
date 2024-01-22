"""Different evaluators are defined for evaluating multiobjective optimization problems."""

import copy

from desdeo.problem.schema import Problem
from desdeo.problem.parser import MathParser, replace_str, SUPPORTED_PARSER_TYPES

from pydantic import BaseModel, Field


class EvaluatorResult(BaseModel):
    """A model to store the results computed by Evaluator."""

    variable_values: dict[str, list[float]] = Field(
        description=(
            "The decision variable values utilized in the evaluation. The keys of the dict are the decision variable"
            " symbols followed by a list of values corresponding to the variable."
        )
    )
    objective_values: dict[str, list[float]] = Field(
        description=(
            "The evaluated objective function values. The keys of the dict are objective function symbols followed"
            " by a list of values corresponding to the objective function."
        )
    )
    extra_values: dict[str, list[float]] | None = Field(
        description=(
            "The evaluated extra function values. The keys of the dict are the extra function symbols followed"
            " by a list of values corresponding to the extra function. Optional."
        ),
        default=None,
    )
    constraint_values: dict[str, list[float]] | None = Field(
        description=(
            "The evaluated constraint values. The keys of the dict"
            "are the constraint symbols followed by a list of values corresponding to the constraint. Optional."
        ),
        default=None,
    )
    scalarization_values: dict[str, list[float]] | None = Field(
        description=(
            "The evaluated scalarization function values. The"
            " keys of the dict are the names of the scalarization functions followed by a list corresponding to the"
            " functions. Optional."
        ),
        default=None,
    )


class EvaluatorError(Exception):
    """Error raised when exceptions are encountered in an Evaluator class."""


class GenericEvaluator:
    """A class for creating evaluators for multiobjective optimization problems.

    The evaluator is to be used with different optimizers. GenericEvaluator is specifically
    for solvers that do not require an exact formulation of the problem, but rather work
    solely on the input and output values of the problem being solved. This evaluator might not
    be suitable for computationally expensive problems, or mixed-integer problems. This
    evaluator is suitable for many Python-based solvers, such as `scipy.optimize.minimize`.

    See the evaluators TO BE DONE for ruther details for approaching other kinds of problems.
    """

    ### Initialization (no need for decision variables yet)
    # 1. Create a math parser with parser type 'evaluator_type'. Defaults to 'polars'.
    # 2. Check for any constants in the definition of the problem. Replace the constants, if they exist,
    #    with their numerical values in all the function expressions found in problem.
    # 3. Parse the function expressions into a dataframe.

    ### Evaluating (we have decision variables to evaluate problem)
    # 1. Evaluate the extra functions (if any) in the dataframe with the decision variables. Store the results
    #    in new columns of the dataframe.
    # 2. Evaluate the objectie functions based on the decision variables and the extra function values (if any).
    #    Store the results in the dataframe in their own columns.
    # 3. Evaluate the constraints (if any) based on the decision variables and extra function values (if any).
    #    Store the results in the dataframe in their own columns.
    # 4. Evalute the scalarization functions (if any) based on the objective function values and extra function values
    #    (if any). Store the results in the dataframe in their own columns.
    # 5. Return a pydantic dataclass with the results (decision variables, objective function values, constraint values,
    #    and scalarization function valeus).
    # 6. End.

    def __init__(self, problem: Problem, parser_type: str = "polars"):
        """Create an evaluator for a multiobjective optimization problem.

        Args:
            problem (Problem): The problem as a pydantic 'Problem' data class.
            parser_type (str): The type of parser used to parse the problem into a format
                that can be evaluated. Default 'polars'.
        """
        # Create a MathParser of type 'evaluator_type'.
        if parser_type not in SUPPORTED_PARSER_TYPES:
            msg = (
                f"The provided 'parser_type' '{parser_type}' is not supported. Must be one of {SUPPORTED_PARSER_TYPES}."
            )
            raise EvaluatorError(msg)

        parser = MathParser(parser=parser_type)

        # This stores the reference to the original problem. This should not be modified directly!
        self.__original_problem = problem

        # This is the local version of the original problem and considers all the changes done
        # to it in the evaluator.
        self._local_problem = copy.deepcopy(problem)

        # Gather any constants of the problem definition.
        self.problem_constants = self._local_problem.constants

        # Gather the objective functions
        self.problem_objectives = self._local_problem.objectives

        # Gather any constraints
        self.problem_constraints = self._local_problem.constraints

        # Gather any extra functions
        self.problem_extra = self._local_problem.extra_funcs

        # Gather any scalarization functions
        self.problem_scalarization = self._local_problem.scalarizations_funcs

        # If any constants are defined in problem, replace their symbol with the defined numerical
        # value in all the function expressions found in the Problem.
        if self.problem_constants is not None:
            # Objectives are always defined, cannot be None
            for obj in self.problem_objectives:
                for c in self.problem_constants:
                    obj.func = replace_str(obj.func, c.symbol, c.value)

            # Do the same for any constraint expressions as well.
            if self.problem_constraints is not None:
                for con in self.problem_constraints:
                    for c in self.problem_constants:
                        con.func = replace_str(con.func, c.symbol, c.value)

            # Do the same for any extra functions
            if self.problem_extra is not None:
                for extra in self.problem_extra:
                    for c in self.problem_constants:
                        extra.func = replace_str(extra.func, c.symbol, c.value)

            # Do the same for any scalarization functions
            if self.problem_scalarization is not None:
                for scal in self.problem_scalarization:
                    for c in self.problem_constants:
                        scal.func = replace_str(scal.func, c.symbol, c.value)

        # Parse all functions into expressions
        if parser_type == "polars":
            self.objective_expressions = [parser.parse(obj.func) for obj in self.problem_objectives]
            if self.problem_constraints is not None:
                self.constraint_expressions = [parser.parse(con.func) for con in self.problem_constraints]

    def evaluate(self, xs: dict[str, list[float | int | bool]]) -> EvaluatorResult:
        """Evaluate the problem with the given decision variable values.

        Args:
            xs (dict[str, list[float  |  int  |  bool]]): a dict with the decision variable names
            as the keys followed by the corresponding decision variable values stored in a list.
            Each list in the dict should contain the same number of values.

        Returns:
            EvaluatorResult: the results of the evaluation. See `EvaluatorResult`.
        """
        ...
