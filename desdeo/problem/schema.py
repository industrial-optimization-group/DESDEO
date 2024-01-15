"""Schema for the problem definition.

The problem definition is a JSON file that contains the following information:

- Constants
- Variables
- Objectives
- Extra functions
- Scalarization functions
- Evaluated solutions and their info

"""


from enum import Enum

from pydantic import BaseModel, Field


VariableType = float | int | bool


class VariableTypeEnum(str, Enum):
    """An enumerator for possible variable types."""

    real = "real"
    integer = "integer"
    binary = "binary"


class Constant(BaseModel):
    """Model for a constant."""

    name: str = Field(
        description=(
            "Descriptive name of the constant. This can be used in UI and visualizations.",
            " Example: 'maximum cost'.",
        ),
    )
    symbol: str = Field(
        description=(
            "Symbol to represent the constant. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'c_1'."
        ),
    )
    value: VariableType = Field(description="Value of the constant.")


class Variable(BaseModel):
    """Model for a variable."""

    name: str = Field(
        description="Descriptive name of the variable. This can be used in UI and visualizations. Example: 'velocity'."
    )
    symbol: str = Field(
        description=(
            "Symbol to represent the variable. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'v_1'."
        ),
    )
    variable_type: VariableTypeEnum = Field(description="Type of the variable. Can be real, integer or binary.")
    lowerbound: VariableType = Field(description="Lower bound of the variable.")
    upperbound: VariableType = Field(description="Upper bound of the variable.")
    initial_value: VariableType | None = Field(
        description="Initial value of the variable. This is optional.",
    )


class ExtraFunction(BaseModel):
    """Model for extra functions.

    These functions can, e.g., be functions that are re-used in the problem formulation, or
    they are needed for other computations related to the problem.
    """

    name: str = Field(
        description=("Descriptive name of the function. Example: 'normalization'"),
    )
    symbol: str = Field(
        description=(
            "Symbol to represent the function. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'avg'."
        ),
    )
    func: list = Field(
        description=(
            "The string representing the function. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match symbols defined for objective/variable/constant."
        ),
    )


class ScalarizationFunction(BaseModel):
    """Model for scalarization of the problem."""

    name: str = Field(
        description=("Name of the scalarization. Example: 'STOM'"),
    )
    func: list = Field(
        description=(
            "Function representation of the scalarization. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match the symbols defined for objective/variable/constant/extra"
            " function."
        ),
    )


class Objective(BaseModel):
    """Model for an objective function."""

    name: str = Field(
        description=(
            "Descriptive name of the objective function. This can be used in UI and visualizations.",
            " Example: 'time'.",
        ),
    )
    symbol: str = Field(
        description=(
            "Symbol to represent the objective function. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'f_1'."
        ),
    )
    func: list = Field(
        description=(
            "The objective function. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object. The symbols in the function must match the symbols defined for "
            "variable/constant/extra function."
        ),
    )
    maximize: bool = Field(
        description="Whether the objective function is to be maximized or minimized.",
        default=False,
    )
    ideal: float | None = Field(
        description="Ideal value of the objective. This is optional.",
    )
    nadir: float | None = Field(
        description="Nadir value of the objective. This is optional.",
    )


class Constraint(BaseModel):
    """Model for a constraint function."""

    name: str = Field(
        description=(
            "Descriptive name of the constraint. This can be used in UI and visualizations."
            " Example: 'maximum length'"
        ),
    )
    symbol: str = Field(
        description=(
            "Symbol to represent the constraint. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'g_1'."
        ),
    )
    func: list = Field(
        description=(
            "Function of the constraint. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match objective/variable/constant shortnames."
        ),
    )


class EvaluatedInfo(BaseModel):
    """Model to represent information about an evaluated solution or solutions to the problem.

    This model may be extended as needed.
    """

    source: str = Field(description="The source of the evaluated solution(s). E.g., an optimization method's name.")
    dominated: bool | None = Field(description="Optional. Are the solutions dominated?")


class VariableValue(BaseModel):
    """Model to represent a concrete value of a decision variable."""

    value: VariableType = Field(description="The value of the variable.")


class DecisionVector(BaseModel):
    """Model to represent a decision vector."""

    values: list[VariableValue] = Field(description="The values contained in the decision vector.")


class EvaluatedSolutions(BaseModel):
    """Model to represent the evaluated objective values of a decision vector.

    The decision vectors 'decision_vectors' and objective vectors
    'objective_vector' correspond to each other based on their ordering. I.e.,
    the evaluated objective function values for the decision vector at position i
    (decision_vectors[i]) are represented by the objective vector at position i
    (objective_vector[i]).
    """

    info: EvaluatedInfo = Field(description="Information about the evaluated solutions.")
    decision_vectors: list[DecisionVector] = Field(description="A list of the evaluated decision vectors.")
    objective_vectors: list[list[float]] = Field(
        description="A list of the values of the evaluated objective functions."
    )


class Problem(BaseModel):
    """Model for a problem definition."""

    name: str = Field(
        description="Name of the problem.",
    )
    description: str = Field(
        description="Description of the problem.",
    )
    constants: list[Constant] = Field(
        description="List of constants.",
    )
    variables: list[Variable] = Field(
        description="List of variables.",
    )
    objectives: list[Objective] = Field(
        description="List of objectives.",
    )
    constraints: list[Constraint] | None = Field(
        description="Optional list of constraints.",
    )
    extra_funcs: list[ExtraFunction] | None = Field(
        description="Optional list of extra functions. Use this if some function is repeated multiple times.",
    )
    scalarizations_funcs: list[ScalarizationFunction] | None = Field(
        description="Optional list of scalarization functions representing the problem."
    )
    evaluated_solutions: list[EvaluatedSolutions] | None = Field(
        description="Optional list of evaluated solutions of the problem."
    )


"""
class DataObjective(Objective):
"""
"""Model for a data-based objective definition."""
"""

    func: list | None = Field(
        description=(
            "Optional analytical function of the objective. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object. The symbols in the function must match variable/constant shortnames."
        ),
    )
"""

"""
class DataProblem(BaseModel):
"""
"""Model for a data-based problem definition."""
"""

    name: str = Field(
        description="Name of the problem.",
    )
    description: str = Field(
        description="Description of the problem.",
    )
    variables: list[Variable] = Field(
        description="List of variables.",
    )
    objectives: list[DataObjective] = Field(
        description="List of objectives.",
    )
    constraints: list[Constraint] | None = Field(
        description="Optional list of constraints.",
    )
    extra_funcs: list[ExtraFuncs] | None = Field(
        description="Optional list of extra functions. Use this if some function is repeated multiple times.",
    )
    data: pl.DataFrame = Field(
        description=(
            "Dataframe containing the data. Each row is a data point."
            " Each column is a variable, objective, or constraint.",
        ),
    )
"""

if __name__ == "__main__":
    # import erdantic as erd

    # diagram = erd.create(Problem)
    # diagram.draw("problem_map.png")

    constant_model = Constant(name="constant example", symbol="c", value=42.1)
    # print(Constant.schema_json(indent=2))
    # print(constant_model.model_dump_json(indent=2))

    variable_model = Variable(
        name="example variable",
        symbol="x_1",
        variable_type="real",
        lowerbound=-0.75,
        upperbound=11.3,
        initial_value=4.2,
    )
    # print(Variable.schema_json(indent=2))
    # print(variable_model.model_dump_json(indent=2))

    objective_model = Objective(
        name="example objective",
        symbol="f_1",
        func=["Divide", ["Add", "x_1", 3], 2],
        maximize=False,
        ideal=-3.3,
        nadir=5.2,
    )
    # print(Objective.schema_json(indent=2))
    # print(objective_model.model_dump_json(indent=2))

    constraint_model = Constraint(
        name="example constraint", symbol="g_1", func=["Less", ["Add", ["Divide", "x_1", 2], "c"], 4.2]
    )
    # print(Constraint.schema_json(indent=2))
    # print(constraint_model.model_dump_json(indent=2))

    extra_func_model = ExtraFunction(name="example extra function", symbol="m", func=["Divide", "f_1", 100])
    # print(ExtraFunction.schema_json(indent=2))
    # print(extra_func_model.model_dump_json(indent=2))

    scalarization_function_model = ScalarizationFunction(
        name="Achievement scalarizing function",
        func=["Max", ["Multiply", "w_1", ["Add", "f_1", -1.1]], ["Multiply", "w_2", ["Add", "f_2", -2.2]]],
    )
    # print(ScalarizationFunction.schema_json(indent=2))
    # print(scalarization_function_model.model_dump_json(indent=2))

    variable_value_model = VariableValue(value=4.2)
    # print(VariableValue.schema_json(indent=2))
    # print(variable_value_model.model_dump_json(indent=2))

    decision_vector_model = DecisionVector(
        values=[VariableValue(value=4.2), VariableValue(value=-1.2), VariableValue(value=6.6)]
    )
    # print(DecisionVector.schema_json(indent=2))
    # print(decision_vector_model.model_dump_json(indent=2))

    evaluated_info_model = EvaluatedInfo(source="NSGA-III", dominated=False)
    # print(EvaluatedInfo.schema_json(indent=2))
    # print(evaluated_info_model.model_dump_json(indent=2))

    evaluated_solutions_model = EvaluatedSolutions(
        info=evaluated_info_model,
        decision_vectors=[decision_vector_model, decision_vector_model, decision_vector_model],
        objective_vectors=[[1, 2, 3], [1, 2, 3], [1, 2, 3]],
    )
    # print(EvaluatedSolutions.schema_json(indent=2))
    # print(evaluated_solutions_model.model_dump_json(indent=2))
