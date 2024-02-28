"""Schema for the problem definition.

The problem definition is a JSON file that contains the following information:

- Constants
- Variables
- Objectives
- Extra functions
- Scalarization functions
- Evaluated solutions and their info

"""


from collections import Counter
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from desdeo.problem.infix_parser import InfixExpressionParser

VariableType = float | int | bool


def parse_infix_to_func(cls, v: str | list) -> list:
    """Validator that checks if the 'func' field is of type str or list.

    If str, then it is assumed the string represents the func in infix notation. The string
    is parsed in the validator. If list, then the func is assumed to be represented in Math JSON format.

    Args:
        v (str | list): The func to be validated.

    Raises:
        ValueError: v is neither an instance of str or a list.

    Returns:
        list: The func represented in Math JSON format.
    """
    if v is None:
        return v
    # Check if v is a string (infix expression), then parse it
    if isinstance(v, str):
        parser = InfixExpressionParser()
        return parser.parse(v)
    # If v is already in the correct format (a list), just return it
    if isinstance(v, list):
        return v

    # Raise an error if v is neither a string nor a list
    msg = f"func must be a string (infix expression) or a list, got {type(v)}"
    raise ValueError(msg)


class VariableTypeEnum(str, Enum):
    """An enumerator for possible variable types."""

    real = "real"
    integer = "integer"
    binary = "binary"


class ConstraintTypeEnum(str, Enum):
    """An enumerator for supported constraint expression types."""

    EQ = "="  # equal
    LTE = "<="  # less than or equal


class ObjectiveTypeEnum(str, Enum):
    """An enumerator for supported objective function types."""

    analytical = "analytical"
    data_based = "data_based"


class Constant(BaseModel):
    """Model for a constant."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description=(
            "Descriptive name of the constant. This can be used in UI and visualizations." " Example: 'maximum cost'."
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

    model_config = ConfigDict(frozen=True)

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
    lowerbound: VariableType | None = Field(description="Lower bound of the variable.", default=None)
    upperbound: VariableType | None = Field(description="Upper bound of the variable.", default=None)
    initial_value: VariableType | None = Field(
        description="Initial value of the variable. This is optional.", default=None
    )


class ExtraFunction(BaseModel):
    """Model for extra functions.

    These functions can, e.g., be functions that are re-used in the problem formulation, or
    they are needed for other computations related to the problem.
    """

    model_config = ConfigDict(frozen=True)

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

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)


class ScalarizationFunction(BaseModel):
    """Model for scalarization of the problem."""

    name: str = Field(description=("Name of the scalarization."), frozen=True)
    symbol: str | None = Field(
        description=(
            "Optional symbol to represent the scalarization function. This may be used in UIs and visualizations."
        ),
        default=None,
        frozen=False,
    )
    func: list = Field(
        description=(
            "Function representation of the scalarization. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match the symbols defined for objective/variable/constant/extra"
            " function."
        ),
        frozen=True,
    )

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)


class Objective(BaseModel):
    """Model for an objective function."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description=(
            "Descriptive name of the objective function. This can be used in UI and visualizations." " Example: 'time'."
        ),
    )
    symbol: str = Field(
        description=(
            "Symbol to represent the objective function. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'f_1'."
        ),
    )
    func: list | None = Field(
        description=(
            "The objective function. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object. The symbols in the function must match the symbols defined for "
            "variable/constant/extra function. Can be 'None' for 'data_based' objective functions."
        ),
    )
    maximize: bool = Field(
        description="Whether the objective function is to be maximized or minimized.",
        default=False,
    )
    ideal: float | None = Field(description="Ideal value of the objective. This is optional.", default=None)
    nadir: float | None = Field(description="Nadir value of the objective. This is optional.", default=None)

    objective_type: ObjectiveTypeEnum = Field(
        description=(
            "The type of objective function. 'analytical' means the objective function value is calculated "
            "based on 'func'. 'data_based' means the objective function value should be retrieved from a table. "
            "In case of 'data_based' objective function, the 'func' field is ignored. Defaults to 'analytical'."
        ),
        default=ObjectiveTypeEnum.analytical,
    )

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)


class Constraint(BaseModel):
    """Model for a constraint function."""

    model_config = ConfigDict(frozen=True)

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
    cons_type: ConstraintTypeEnum = Field(
        description=(
            "The type of the constraint. Constraints are assumed to be in a standard form where the supplied 'func'"
            " expression is on the left hand side of the constraint's expression, and on the right hand side a zero"
            " value is assume. The comparison between the left hand side and right hand side is either and quality"
            " comparison ('=') or lesser than equal comparison ('<=')."
        )
    )
    func: list = Field(
        description=(
            "Function of the constraint. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match objective/variable/constant shortnames."
        ),
    )

    linear: bool = Field(
        description="Whether the constraint is linear or not. Defaults to True, e.g., a linear constraint is assumed.",
        default=True,
    )

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)


class EvaluatedInfo(BaseModel):
    """Model to represent information about an evaluated solution or solutions to the problem.

    This model may be extended as needed.
    """

    model_config = ConfigDict(frozen=True)

    source: str = Field(description="The source of the evaluated solution(s). E.g., an optimization method's name.")
    dominated: bool | None = Field(description="Optional. Are the solutions dominated?", default=None)


class EvaluatedSolutions(BaseModel):
    """Model to represent the evaluated objective values of a decision vector.

    The decision vectors 'decision_vectors' and objective vectors
    'objective_vector' correspond to each other based on their ordering. I.e.,
    the evaluated objective function values for the decision vector at position i
    (decision_vectors[i]) are represented by the objective vector at position i
    (objective_vector[i]).
    """

    model_config = ConfigDict(frozen=True)

    info: EvaluatedInfo = Field(description="Information about the evaluated solutions.")
    decision_vectors: list[list[VariableType]] = Field(description="A list of the evaluated decision vectors.")
    objective_vectors: list[list[float]] = Field(
        description="A list of the values of the evaluated objective functions."
    )


class DiscreteDefinition(BaseModel):
    """Model to represent discrete objective function and decision variable pairs.

    Used with Objectives of type 'data_based'. Each of the decision variable values and objective
    functions values are ordered in their respective dict entries. This means that the
    decision variable values found at 'variable_values['x_i'][j]' correspond to the objective
    function values found at 'objective_values['f_i'][j] for all i and some j.
    """

    model_config = ConfigDict(frozen=True)

    variable_values: dict[str, list[VariableType]] = Field(
        description=(
            "A dictionary with decision variable values. Each dict key points to a list of all the decision "
            "variable values available for the decision variable given in the key. "
            "The keys must match the 'symbols' defined for the decision variables."
        )
    )
    objective_values: dict[str, list[float]] = Field(
        description=(
            "A dictionary with objective function values. Each dict key points to a list of all the objective "
            "function values available for the objective function given in the key. The keys must match the 'symbols' "
            "defined for the objective functions."
        )
    )


class Problem(BaseModel):
    """Model for a problem definition."""

    model_config = ConfigDict(frozen=True)
    model_config["from_attributes"] = True

    _scalarization_index: int = PrivateAttr(default=1)
    # TODO: make init to communicate the _scalarization_index to a new model

    @model_validator(mode="after")
    def set_default_scalarization_names(self) -> "Problem":
        """Check the scalarization functions for symbols with value 'None'.

        If found, names them systematically
        'scal_i', where 'i' is a running index stored in an instance attribute.
        """
        if self.scalarizations_funcs is None:
            return self

        for func in self.scalarizations_funcs:
            if func.symbol is None:
                func.symbol = f"scal_{self._scalarization_index}"
                self._scalarization_index += 1

        return self

    @model_validator(mode="after")
    def check_for_non_unique_symbols(self) -> "Problem":
        """Check that all the symbols defined in the different fields are unique."""
        symbols = self.get_all_symbols()

        # symbol is always populated
        symbol_counts = Counter(symbols)

        # collect duplicates, if they exist
        duplicates = {symbol: count for symbol, count in symbol_counts.items() if count > 1}

        if duplicates:
            # if any duplicates are found, raise a value error and report the duplicate symbols.
            msg = "Non-unique symbols found in the Problem model."
            for symbol, count in duplicates.items():
                msg += f" Symbol '{symbol}' occurs {count} times."

            raise ValueError(msg)

        return self

    def get_all_symbols(self) -> list[str]:
        """Collects and returns all the symbols symbols currently defined in the model."""
        # collect all symbols
        symbols = [variable.symbol for variable in self.variables]
        symbols += [objective.symbol for objective in self.objectives]
        if self.constants is not None:
            symbols += [constant.symbol for constant in self.constants]
        if self.constraints is not None:
            symbols += [constraint.symbol for constraint in self.constraints]
        if self.extra_funcs is not None:
            symbols += [extra.symbol for extra in self.extra_funcs]
        if self.scalarizations_funcs is not None:
            symbols += [scalarization.symbol for scalarization in self.scalarizations_funcs]

        return symbols

    def add_scalarization(self, new_scal: ScalarizationFunction) -> "Problem":
        """Adds a new scalarization function to the model.

        If no symbol is defined, adds a name with the format 'scal_i'.

        Args:
            new_scal (ScalarizationFunction): Scalarization functions to be added to the model.

        Raises:
            ValueError: Raised when a ScalarizationFunction is given with a symbol that already exists in the model.
        """
        if new_scal.symbol is None:
            new_scal.symbol = f"scal_{self._scalarization_index}"
            self._scalarization_index += 1

        if self.scalarizations_funcs is None:
            return self.model_copy(update={"scalarizations_funcs": [new_scal]})
        symbols = self.get_all_symbols()
        symbols.append(new_scal.symbol)
        symbol_counts = Counter(symbols)
        duplicates = {symbol: count for symbol, count in symbol_counts.items() if count > 1}

        if duplicates:
            msg = "Non-unique symbols found in the Problem model."
            for symbol, count in duplicates.items():
                msg += f" Symbol '{symbol}' occurs {count} times."

            raise ValueError(msg)

        return self.model_copy(update={"scalarizations_funcs": [*self.scalarizations_funcs, new_scal]})

    name: str = Field(
        description="Name of the problem.",
    )
    description: str = Field(
        description="Description of the problem.",
    )
    constants: list[Constant] | None = Field(description="List of constants.", default=None)
    variables: list[Variable] = Field(
        description="List of variables.",
    )
    objectives: list[Objective] = Field(
        description="List of objectives.",
    )
    constraints: list[Constraint] | None = Field(
        description="Optional list of constraints.",
        default=None,
    )
    extra_funcs: list[ExtraFunction] | None = Field(
        description="Optional list of extra functions. Use this if some function is repeated multiple times.",
        default=None,
    )
    scalarizations_funcs: list[ScalarizationFunction] | None = Field(
        description="Optional list of scalarization functions representing the problem.", default=None
    )
    evaluated_solutions: list[EvaluatedSolutions] | None = Field(
        description="Optional list of evaluated solutions of the problem.", default=None
    )
    discrete_definition: DiscreteDefinition | None = Field(
        description=(
            "Optional. Required when there are one or more 'data_based' Objectives. The corresponding values "
            "of the 'data_based' objective function will be fetched from this with the given variable values. "
            "Defaults to 'None'."
        ),
        default=None,
    )


if __name__ == "__main__":
    # import erdantic as erd

    # diagram = erd.create(Problem)
    # diagram.draw("problem_map.png")

    constant_model = Constant(name="constant example", symbol="c", value=42.1)
    # print(Constant.schema_json(indent=2))
    # print(constant_model.model_dump_json(indent=2))

    variable_model_1 = Variable(
        name="example variable",
        symbol="x_1",
        variable_type=VariableTypeEnum.real,
        lowerbound=-0.75,
        upperbound=11.3,
        initial_value=4.2,
    )
    variable_model_2 = Variable(
        name="example variable",
        symbol="x_2",
        variable_type=VariableTypeEnum.real,
        lowerbound=-0.75,
        upperbound=11.3,
        initial_value=4.2,
    )
    variable_model_3 = Variable(
        name="example variable",
        symbol="x_3",
        variable_type=VariableTypeEnum.real,
        lowerbound=-0.75,
        upperbound=11.3,
        initial_value=4.2,
    )
    # print(Variable.schema_json(indent=2))
    # print(variable_model.model_dump_json(indent=2))

    objective_model_1 = Objective(
        name="example objective",
        symbol="f_1",
        func=["Divide", ["Add", "x_1", 3], 2],
        maximize=False,
        ideal=-3.3,
        nadir=5.2,
    )
    objective_model_2 = Objective(
        name="example objective",
        symbol="f_2",
        func=["Divide", ["Add", "x_1", 3], 2],
        maximize=False,
        ideal=-3.3,
        nadir=5.2,
    )
    objective_model_3 = Objective(
        name="example objective",
        symbol="f_3",
        func=["Divide", ["Add", "x_1", 3], 2],
        maximize=False,
        ideal=-3.3,
        nadir=5.2,
    )
    # print(Objective.schema_json(indent=2))
    # print(objective_model.model_dump_json(indent=2))

    constraint_model = Constraint(
        name="example constraint",
        symbol="g_1",
        func=["Add", ["Add", ["Divide", "x_1", 2], "c"], -4.2],
        cons_type=ConstraintTypeEnum.LTE,
    )
    # print(Constraint.schema_json(indent=2))
    # print(constraint_model.model_dump_json(indent=2))

    extra_func_model = ExtraFunction(name="example extra function", symbol="m", func=["Divide", "f_1", 100])
    # print(ExtraFunction.schema_json(indent=2))
    # print(extra_func_model.model_dump_json(indent=2))

    scalarization_function_model = ScalarizationFunction(
        name="Achievement scalarizing function",
        symbol="S",
        func=["Max", ["Multiply", "w_1", ["Add", "f_1", -1.1]], ["Multiply", "w_2", ["Add", "f_2", -2.2]]],
    )
    # print(ScalarizationFunction.schema_json(indent=2))
    # print(scalarization_function_model.model_dump_json(indent=2))

    evaluated_info_model = EvaluatedInfo(source="NSGA-III", dominated=False)
    # print(EvaluatedInfo.schema_json(indent=2))
    # print(evaluated_info_model.model_dump_json(indent=2))

    evaluated_solutions_model = EvaluatedSolutions(
        info=evaluated_info_model,
        decision_vectors=[[4.2, -1.2, 6.6], [4.2, -1.2, 6.6], [4.2, -1.2, 6.6]],
        objective_vectors=[[1, 2, 3], [1, 2, 3], [1, 2, 3]],
    )
    # print(EvaluatedSolutions.schema_json(indent=2))
    # print(evaluated_solutions_model.model_dump_json(indent=2))

    problem_model = Problem(
        name="Example problem",
        description="This is an example of a the JSON object of the 'Problem' model.",
        constants=[constant_model],
        variables=[variable_model_1, variable_model_2, variable_model_3],
        objectives=[objective_model_1, objective_model_2, objective_model_3],
        constraints=[constraint_model],
        extra_funcs=[extra_func_model],
        scalarizations_funcs=[scalarization_function_model],
        evaluated_solutions=[evaluated_solutions_model],
    )

    # print(problem_model.model_dump_json(indent=2))
