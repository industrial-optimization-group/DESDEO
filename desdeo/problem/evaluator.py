"""Different evaluators are defined for evaluating multiobjective optimization problems."""

from desdeo.problem.schema import Problem
from desdeo.problem.parser import MathParser, replace_str

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


class Evaluator:
    """A class for creating evaluators for multiobjective optimization problems."""

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

    def __init__(self, problem: Problem, evaluator_type: str = "polars"):
        """Create an evaluator for a multiobjective optimization problem.

        Args:
            problem (Problem): The problem as a pydantic 'Problem' data class.
            evaluator_type (str): The type of evaluator. Default 'polars'.
        """
        # 1. Create a MathParser of type 'evaluator_type'.
        ...
        # 2. If any constants are defined in problem, replace their symbol with the defined numerical
        #    value in all the function expressions found in the Problem.
        ...
        # 3. Parse said function expressions into a dataframe.
        ...
        # 4. The dataframe is stored in the class instance.
        self.dataframe = None

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
