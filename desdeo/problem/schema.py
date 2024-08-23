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
from collections.abc import Iterable
from enum import Enum
from typing import Annotated, Any, Literal, TypeAliasType

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from desdeo.problem.infix_parser import InfixExpressionParser

VariableType = float | int | bool


def tensor_custom_error_validator(value: Any, handler: ValidatorFunctionWrapHandler, _info: ValidationInfo) -> Any:
    """Custom error handler to simplify error messages related to recursive tensor types.

    Args:
        value (Any): input value to be validated.
        handler (ValidatorFunctionWrapHandler): handler to check the values.
        _info (ValidationInfo): info related to the validation of the value.

    Raises:
        PydanticCustomError: when the value is an invalid tensor type.

    Returns:
        Any: a valid tensor.
    """
    try:
        return handler(value)
    except ValidationError as exc:
        raise PydanticCustomError("invalid tensor", "Input is not a valid tensor") from exc


Tensor = TypeAliasType(
    "Tensor",
    Annotated[
        list["Tensor"] | list[VariableType] | VariableType | Literal["List"],
        WrapValidator(tensor_custom_error_validator),
    ],
)


def parse_infix_to_func(cls: "Problem", v: str | list) -> list:
    """Validator that checks if the 'func' field is of type str or list.

    If str, then it is assumed the string represents the func in infix notation. The string
    is parsed in the validator. If list, then the func is assumed to be represented in Math JSON format.

    Args:
        cls: the class of the pydantic model the validator is applied to.
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
    msg = f"The function expressions must be a string (infix expression) or a list. Got {type(v)}."
    raise ValueError(msg)


def parse_scenario_key_singleton_to_list(cls: "Problem", v: str | list[str]) -> list[str] | None:
    """Validator that checks the type of a scenario key.

    If the type is a list, it will be returned as it is. If it is a string,
    then a list with the single string is returned. Else, a ValueError is raised.

    Args:
        cls: the class of the pydantic model the validator is applied to.
        v (str | list[str]): the scenario key, or keys, to be validated.

    Raises:
        ValueError: raised when `v` it neither a string or a list.

    Returns:
        list[str]: a list with scenario keys.
    """
    if v is None:
        return v
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return v

    msg = f"The scenario keys must be either a list of strings, or a single string. Got {type(v)}."
    raise ValueError(msg)


def parse_list_to_mathjson(cls: "TensorVariable", v: Tensor | None) -> list:
    """Validator that makes sure a nested Python list is represented as tensor following the MathJSON convention.

    Args:
        cls (TensorVariable): the class of the pydantic model the validator is applied to.
        v (Tensor | None): the nested lists to be validated.

    Returns:
        list: a tensor following the MathJSON conventions.
    """
    if v is None:
        return v
    # recursively parse into a MathJSON representation
    if isinstance(v, list) and len(v) > 0:
        if isinstance(v[0], list):
            # recursive case, encountered list
            return ["List", *[parse_list_to_mathjson(TensorVariable, v_element) for v_element in v]]
        if isinstance(v[0], VariableType):
            # terminal case, encountered a VariableType
            return ["List", *v]

        # if anything else is encountered, raise an error
        msg = "Encountered value that is not a valid VariableType nor a list."
        raise ValueError(msg)

    msg = f"The tensor must a Python list (of lists). Got {type(v)}."
    raise ValueError(msg)


def get_tensor_values(
    values: Iterable[VariableType | Iterable[VariableType]] | None,
) -> Iterable[VariableType | Iterable[VariableType]] | None:
    """Return the values for a given attribute as a nested Python list with shape `self.shape`.

    Removes the 'List' entries from the JSON format to give a Python compatible list.

    Arguments:
        values (Iterable[VariableType | Iterable[VariableType]] | None): the values that should be extracted as a
            Python list.

    Returns:
        list[VariableType] | Iterable[list[VariableType]] | None: a list with shape `self.shape` with the
            values defined for the variable.
    """
    if values is None:
        return values

    if isinstance(values, list) and len(values) > 1:
        if values[0] == "List" and isinstance(values[1], list):
            # recursive case, encountered list
            return [get_tensor_values(v_element) for v_element in values[1:]]
        if values[0] == "List":
            # terminal case, encountered a VariableType
            return [*values[1:]]

        # if anything else is encountered, raise an error
        msg = "Encountered value that is not a valid VariableType nor a list."
        raise ValueError(msg)

    msg = f"Values must be a valid MathJSON vector. Got {type(values)}."
    raise ValueError(msg)


class VariableTypeEnum(str, Enum):
    """An enumerator for possible variable types."""

    real = "real"
    """A continuous variable."""
    integer = "integer"
    """An integer variable."""
    binary = "binary"
    """A binary variable."""


class VariableDomainTypeEnum(str, Enum):
    """An enumerator for the possible variable type domains of a problem."""

    continuous = "continuous"
    """All variables are real valued."""
    integer = "integer"
    """All variables are integer or binary valued."""
    mixed = "mixed"
    """Some variables are continuos, some are integer or binary."""


class ConstraintTypeEnum(str, Enum):
    """An enumerator for supported constraint expression types."""

    EQ = "="
    """An equality constraint."""
    LTE = "<="  # less than or equal
    """An inequality constraint of type 'less than or equal'."""


class ObjectiveTypeEnum(str, Enum):
    """An enumerator for supported objective function types."""

    analytical = "analytical"
    """An objective function with an analytical formulation. E.g., it can be
    expressed with mathematical expressions, such as x_1 + x_2."""
    data_based = "data_based"
    """A data-based objective function. It is assumed that when such an
    objective is present in a `Problem`, then there is a
    `DiscreteRepresentation` available with values representing the objective
    function."""


class Constant(BaseModel):
    """Model for a constant."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description=(
            "Descriptive name of the constant. This can be used in UI and visualizations." " Example: 'maximum cost'."
        ),
    )
    """Descriptive name of the constant. This can be used in UI and visualizations." " Example: 'maximum cost'."""
    symbol: str = Field(
        description=(
            "Symbol to represent the constant. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'c_1'."
        ),
    )
    """ Symbol to represent the constant. This will be used in the rest of the
    problem definition.  It may also be used in UIs and visualizations. Example:
    'c_1'."""
    value: VariableType = Field(description="The value of the constant.")
    """The value of the constant."""


class TensorConstant(BaseModel):
    """Model for a tensor containing constant values."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str = Field(description="Descriptive name of the tensor representing the values. E.g., 'distances'")
    """Descriptive name of the tensor representing the values. E.g., 'distances'"""
    symbol: str = Field(
        description=(
            "Symbol to represent the constant. This will be used in the rest of the problem definition."
            " Notice that the elements of the tensor will be represented with the symbol followed by"
            " indices. E.g., the first element of the third element of a 2-dimensional tensor,"
            " is represented by 'x_1_3', where 'x' is the symbol given to the TensorVariable."
            " Note that indexing starts from 1."
        )
    )
    """
    Symbol to represent the constant. This will be used in the rest of the problem definition.
    Notice that the elements of the tensor will be represented with the symbol followed by
    indices. E.g., the first element of the third element of a 2-dimensional tensor,
    is represented by 'x_1_3', where 'x' is the symbol given to the TensorVariable.
    Note that indexing starts from 1.
    """
    shape: list[int] = Field(
        description=(
            "A list of the dimensions of the tensor, "
            "e.g., `[2, 3]` would indicate a matrix with 2 rows and 3 columns."
        )
    )
    """A list of the dimensions of the tensor, e.g., `[2, 3]` would indicate a matrix with 2 rows and 3 columns.
    """
    values: Tensor = Field(
        description=(
            "A list of lists, with the elements representing the values of each constant element in the tensor. "
            "E.g., `[[5, 22, 0], [14, 5, 44]]`."
        ),
    )
    """A list of lists, with the elements representing the initial values of each constant element in the tensor.
    E.g., `[[5, 22, 0], [14, 5, 44]]`."""

    _parse_list_to_mathjson = field_validator("values", mode="before")(parse_list_to_mathjson)

    def get_values(self) -> Iterable[VariableType | Iterable[VariableType]] | None:
        """Return the constant values as a Python iterable (e.g., list of list)."""
        return get_tensor_values(self.values)


class Variable(BaseModel):
    """Model for a variable."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description="Descriptive name of the variable. This can be used in UI and visualizations. Example: 'velocity'."
    )
    """Descriptive name of the variable. This can be used in UI and visualizations. Example: 'velocity'."""
    symbol: str = Field(
        description=(
            "Symbol to represent the variable. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'v_1'."
        ),
    )
    """ Symbol to represent the variable. This will be used in the rest of the
    problem definition.  It may also be used in UIs and visualizations. Example:
    'v_1'."""
    variable_type: VariableTypeEnum = Field(description="Type of the variable. Can be real, integer or binary.")
    """Type of the variable. Can be real, integer or binary."""
    lowerbound: VariableType | None = Field(description="Lower bound of the variable.", default=None)
    """Lower bound of the variable. Defaults to `None`."""
    upperbound: VariableType | None = Field(description="Upper bound of the variable.", default=None)
    """Upper bound of the variable. Defaults to `None`."""
    initial_value: VariableType | None = Field(
        description="Initial value of the variable. This is optional.", default=None
    )
    """Initial value of the variable. This is optional. Defaults to `None`."""


class TensorVariable(BaseModel):
    """Model for a tensor, e.g., vector variable."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str = Field(
        description="Descriptive name of the variable. This can be used in UI and visualizations. Example: 'velocity'."
    )
    """Descriptive name of the variable. This can be used in UI and visualizations. Example: 'velocity'."""
    symbol: str = Field(
        description=(
            "Symbol to represent the variable. This will be used in the rest of the problem definition."
            " Notice that the elements of the tensor will be represented with the symbol followed by"
            " indices. E.g., the first element of the third element of a 2-dimensional tensor,"
            " is represented by 'x_1_3', where 'x' is the symbol given to the TensorVariable."
            " Note that indexing starts from 1."
        )
    )
    """
    Symbol to represent the variable. This will be used in the rest of the problem definition.
    Notice that the elements of the tensor will be represented with the symbol followed by
    indices. E.g., the first element of the third element of a 2-dimensional tensor,
    is represented by 'x_1_3', where 'x' is the symbol given to the TensorVariable.
    Note that indexing starts from 1.
    """
    variable_type: VariableTypeEnum = Field(
        description=(
            "Type of the variable. Can be real, integer, or binary. "
            "Note that each element of a TensorVariable is assumed to be of the same type."
        )
    )
    """Type of the variable. Can be real, integer, or binary.
    Note that each element of a TensorVariable is assumed to be of the same type."""

    shape: list[int] = Field(
        description=(
            "A list of the dimensions of the tensor, "
            "e.g., `[2, 3]` would indicate a matrix with 2 rows and 3 columns."
        )
    )
    """A list of the dimensions of the tensor,
    e.g., `[2, 3]` would indicate a matrix with 2 rows and 3 columns.
    """
    lowerbounds: Tensor | None = Field(
        description=(
            "A list of lists, with the elements representing the lower bounds of each element. "
            "E.g., `[[1, 2, 3], [4, 5, 6]]`. Defaults to None."
        ),
        default=None,
    )
    """A list of lists, with the elements representing the lower bounds of each element.
    E.g., `[[1, 2, 3], [4, 5, 6]]`. Defaults to None.
    """
    upperbounds: Tensor | None = Field(
        description=(
            "A list of lists, with the elements representing the upper bounds of each element. "
            "E.g., `[[10, 20, 30], [40, 50, 60]]`. Defaults to None."
        ),
        default=None,
    )
    """A list of lists, with the elements representing the lower bounds of each element.
    E.g., `[[1, 2, 3], [4, 5, 6]]`. Defaults to None.
    """
    initial_values: Tensor | None = Field(
        description=(
            "A list of lists, with the elements representing the initial values of each element. "
            "E.g., `[[5, 22, 0], [14, 5, 44]]`. Defaults to None."
        ),
        default=None,
    )
    """A list of lists, with the elements representing the initial values of each element.
    E.g., `[[5, 22, 0], [14, 5, 44]]`. Defaults to None."""

    _parse_list_to_mathjson = field_validator("lowerbounds", "upperbounds", "initial_values", mode="before")(
        parse_list_to_mathjson
    )

    def get_lowerbound_values(self) -> Iterable[VariableType | Iterable[VariableType]] | None:
        """Return the lowerbounds values, if any, as a Python iterable (list of list)."""
        return get_tensor_values(self.lowerbounds)

    def get_upperbound_values(self) -> Iterable[VariableType | Iterable[VariableType]] | None:
        """Return the upperbounds values, if any, as a Python iterable (list of list)."""
        return get_tensor_values(self.upperbounds)

    def get_initial_values(self) -> Iterable[VariableType | Iterable[VariableType]] | None:
        """Return the initial values, if any, as a Python iterable (list of list)."""
        return get_tensor_values(self.initial_values)


class ExtraFunction(BaseModel):
    """Model for extra functions.

    These functions can, e.g., be functions that are re-used in the problem formulation, or
    they are needed for other computations related to the problem.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description=("Descriptive name of the function. Example: 'normalization'."),
    )
    """Descriptive name of the function. Example: 'normalization'."""
    symbol: str = Field(
        description=(
            "Symbol to represent the function. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'avg'."
        ),
    )
    """ Symbol to represent the function. This will be used in the rest of the
    problem definition.  It may also be used in UIs and visualizations. Example:
    'avg'."""
    func: list = Field(
        description=(
            "The string representing the function. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match symbols defined for objective/variable/constant."
        ),
    )
    """ The string representing the function. This is a JSON object that can be
    parsed into a function.  Must be a valid MathJSON object.  The symbols in
    the function must match symbols defined for objective/variable/constant.
    """
    is_linear: bool = Field(
        description="Whether the function expression is linear or not. Defaults to `False`.", default=False
    )
    """Whether the function expression is linear or not. Defaults to `False`."""
    is_convex: bool = Field(
        description="Whether the function expression is convex or not (non-convex). Defaults to `False`.", default=False
    )
    """Whether the function expression is convex or not (non-convex). Defaults to `False`."""
    is_twice_differentiable: bool = Field(
        description="Whether the function expression is twice differentiable or not. Defaults to `False`", default=False
    )
    """Whether the function expression is twice differentiable or not. Defaults to `False`"""
    scenario_keys: list[str] | None = Field(
        description="Optional. The keys of the scenario the extra functions belongs to.", default=None
    )
    """Optional. The keys of the scenarios the extra functions belongs to."""

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)
    _parse_scenario_key_singleton_to_list = field_validator("scenario_keys", mode="before")(
        parse_scenario_key_singleton_to_list
    )


class ScalarizationFunction(BaseModel):
    """Model for scalarization of the problem."""

    name: str = Field(description=("Name of the scalarization function."), frozen=True)
    """Name of the scalarization function."""
    symbol: str | None = Field(
        description=(
            "Optional symbol to represent the scalarization function. This may be used in UIs and visualizations."
        ),
        default=None,
        frozen=False,
    )
    """Optional symbol to represent the scalarization function. This may be used
    in UIs and visualizations. Defaults to `None`."""
    func: list = Field(
        description=(
            "Function representation of the scalarization. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match the symbols defined for objective/variable/constant/extra"
            " function."
        ),
        frozen=True,
    )
    """ Function representation of the scalarization. This is a JSON object that
    can be parsed into a function.  Must be a valid MathJSON object. The
    symbols in the function must match the symbols defined for
    objective/variable/constant/extra function."""
    is_linear: bool = Field(
        description="Whether the function expression is linear or not. Defaults to `False`.", default=False, frozen=True
    )
    """Whether the function expression is linear or not. Defaults to `False`."""
    is_convex: bool = Field(
        description="Whether the function expression is convex or not (non-convex). Defaults to `False`.",
        default=False,
        frozen=True,
    )
    """Whether the function expression is convex or not (non-convex). Defaults to `False`."""
    is_twice_differentiable: bool = Field(
        description="Whether the function expression is twice differentiable or not. Defaults to `False`",
        default=False,
        frozen=True,
    )
    """Whether the function expression is twice differentiable or not. Defaults to `False`"""
    scenario_keys: list[str] = Field(
        description="Optional. The keys of the scenarios the scalarization function belongs to.", default=None
    )
    """Optional. The keys of the scenarios the scalarization function belongs to."""

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)
    _parse_scenario_key_singleton_to_list = field_validator("scenario_keys", mode="before")(
        parse_scenario_key_singleton_to_list
    )


class Objective(BaseModel):
    """Model for an objective function."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description=(
            "Descriptive name of the objective function. This can be used in UI and visualizations." " Example: 'time'."
        ),
    )
    """Descriptive name of the objective function. This can be used in UI and visualizations."""
    symbol: str = Field(
        description=(
            "Symbol to represent the objective function. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'f_1'."
        ),
    )
    """ Symbol to represent the objective function. This will be used in the
    rest of the problem definition.  It may also be used in UIs and
    visualizations. Example: 'f_1'."""
    unit: str | None = Field(
        description=(
            "The unit of the objective function. This is optional. Used in UIs and visualizations. Example: 'seconds'"
            " or 'millions of hectares'."
        ),
        default=None,
    )
    """The unit of the objective function. This is optional. Used in UIs and visualizations. Example: 'seconds' or
    'millions of hectares'. Defaults to `None`."""
    func: list | None = Field(
        description=(
            "The objective function. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object. The symbols in the function must match the symbols defined for "
            "variable/constant/extra function. Can be 'None' for 'data_based' objective functions."
        ),
    )
    """ The objective function. This is a JSON object that can be parsed into a
    function.  Must be a valid MathJSON object. The symbols in the function must
    match the symbols defined for variable/constant/extra function. Can be
    'None' for 'data_based' objective functions."""
    maximize: bool = Field(
        description="Whether the objective function is to be maximized or minimized.",
        default=False,
    )
    """Whether the objective function is to be maximized or minimized. Defaults to `False`."""
    ideal: float | None = Field(description="Ideal value of the objective. This is optional.", default=None)
    """Ideal value of the objective. This is optional. Defaults to `None`."""
    nadir: float | None = Field(description="Nadir value of the objective. This is optional.", default=None)
    """Nadir value of the objective. This is optional. Defaults to `None`."""

    objective_type: ObjectiveTypeEnum = Field(
        description=(
            "The type of objective function. 'analytical' means the objective function value is calculated "
            "based on 'func'. 'data_based' means the objective function value should be retrieved from a table. "
            "In case of 'data_based' objective function, the 'func' field is ignored. Defaults to 'analytical'."
        ),
        default=ObjectiveTypeEnum.analytical,
    )
    """ The type of objective function. 'analytical' means the objective
    function value is calculated based on 'func'. 'data_based' means the
    objective function value should be retrieved from a table.  In case of
    'data_based' objective function, the 'func' field is ignored. Defaults to
    'analytical'. Defaults to 'analytical'."""
    is_linear: bool = Field(
        description="Whether the function expression is linear or not. Defaults to `False`.", default=False
    )
    """Whether the function expression is linear or not. Defaults to `False`."""
    is_convex: bool = Field(
        description="Whether the function expression is convex or not (non-convex). Defaults to `False`.", default=False
    )
    """Whether the function expression is convex or not (non-convex). Defaults to `False`."""
    is_twice_differentiable: bool = Field(
        description="Whether the function expression is twice differentiable or not. Defaults to `False`", default=False
    )
    """Whether the function expression is twice differentiable or not. Defaults to `False`"""
    scenario_keys: list[str] | None = Field(
        description="Optional. The keys of the scenarios the objective function belongs to.", default=None
    )
    """Optional. The keys of the scenarios the objective function belongs to."""

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)
    _parse_scenario_key_singleton_to_list = field_validator("scenario_keys", mode="before")(
        parse_scenario_key_singleton_to_list
    )


class Constraint(BaseModel):
    """Model for a constraint function."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description=(
            "Descriptive name of the constraint. This can be used in UI and visualizations."
            " Example: 'maximum length'."
        ),
    )
    """ Descriptive name of the constraint. This can be used in UI and
    visualizations.  Example: 'maximum length'"""
    symbol: str = Field(
        description=(
            "Symbol to represent the constraint. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'g_1'."
        ),
    )
    """ Symbol to represent the constraint. This will be used in the rest of the
    problem definition.  It may also be used in UIs and visualizations. Example:
    'g_1'.  """
    cons_type: ConstraintTypeEnum = Field(
        description=(
            "The type of the constraint. Constraints are assumed to be in a standard form where the supplied 'func'"
            " expression is on the left hand side of the constraint's expression, and on the right hand side a zero"
            " value is assume. The comparison between the left hand side and right hand side is either and quality"
            " comparison ('=') or lesser than equal comparison ('<=')."
        )
    )
    """ The type of the constraint. Constraints are assumed to be in a standard
    form where the supplied 'func' expression is on the left hand side of the
    constraint's expression, and on the right hand side a zero value is assume.
    The comparison between the left hand side and right hand side is either and
    quality comparison ('=') or lesser than equal comparison ('<=')."""
    func: list = Field(
        description=(
            "Function of the constraint. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match objective/variable/constant symbols."
        ),
    )
    """ Function of the constraint. This is a JSON object that can be parsed
    into a function.  Must be a valid MathJSON object.  The symbols in the
    function must match objective/variable/constant symbols."""

    is_linear: bool = Field(
        description="Whether the constraint is linear or not. Defaults to True, e.g., a linear constraint is assumed.",
        default=True,
    )
    """Whether the constraint is linear or not. Defaults to True, e.g., a linear
    constraint is assumed. Defaults to `True`."""
    is_convex: bool = Field(
        description="Whether the function expression is convex or not (non-convex). Defaults to `False`.", default=False
    )
    """Whether the function expression is convex or not (non-convex). Defaults to `False`."""
    is_twice_differentiable: bool = Field(
        description="Whether the function expression is twice differentiable or not. Defaults to `False`", default=False
    )
    """Whether the function expression is twice differentiable or not. Defaults to `False`"""
    scenario_keys: list[str] | None = Field(
        description="Optional. The keys of the scenarios the constraint belongs to.", default=None
    )
    """Optional. The keys of the scenarios the constraint belongs to."""

    _parse_infix_to_func = field_validator("func", mode="before")(parse_infix_to_func)
    _parse_scenario_key_singleton_to_list = field_validator("scenario_keys", mode="before")(
        parse_scenario_key_singleton_to_list
    )


class DiscreteRepresentation(BaseModel):
    """Model to represent discrete objective function and decision variable pairs.

    Can be used alongside an analytical representation as well.

    Used with Objectives of type 'data_based' by default. Each of the decision
    variable values and objective functions values are ordered in their
    respective dict entries. This means that the decision variable values found
    at `variable_values['x_i'][j]` correspond to the objective function values
    found at `objective_values['f_i'][j]` for all `i` and some `j`.
    """

    model_config = ConfigDict(frozen=True)

    variable_values: dict[str, list[VariableType]] = Field(
        description=(
            "A dictionary with decision variable values. Each dict key points to a list of all the decision "
            "variable values available for the decision variable given in the key. "
            "The keys must match the 'symbols' defined for the decision variables."
        )
    )
    """ A dictionary with decision variable values. Each dict key points to a
    list of all the decision variable values available for the decision variable
    given in the key.  The keys must match the 'symbols' defined for the
    decision variables."""
    objective_values: dict[str, list[float]] = Field(
        description=(
            "A dictionary with objective function values. Each dict key points to a list of all the objective "
            "function values available for the objective function given in the key. The keys must match the 'symbols' "
            "defined for the objective functions."
        )
    )
    """ A dictionary with objective function values. Each dict key points to a
    list of all the objective function values available for the objective
    function given in the key. The keys must match the 'symbols' defined for the
    objective functions."""
    non_dominated: bool = Field(
        description=(
            "Indicates whether the representation consists of non-dominated points or not.",
            "If False, some method can employ non-dominated sorting, which might slow an interactive method down.",
        ),
        default=False,
    )
    """ Indicates whether the representation consists of non-dominated points or
    not.  If False, some method can employ non-dominated sorting, which might
    slow an interactive method down. Defaults to `False`."""


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
        if self.scalarization_funcs is None:
            return self

        for func in self.scalarization_funcs:
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
        if self.scalarization_funcs is not None:
            symbols += [scalarization.symbol for scalarization in self.scalarization_funcs]

        return symbols

    def add_scalarization(self, new_scal: ScalarizationFunction) -> "Problem":
        """Adds a new scalarization function to the model.

        If no symbol is defined, adds a name with the format 'scal_i'.

        Does not modify the original problem model, but instead returns a copy of it with the added
        scalarization function.

        Args:
            new_scal (ScalarizationFunction): Scalarization functions to be added to the model.

        Raises:
            ValueError: Raised when a ScalarizationFunction is given with a symbol that already exists in the model.

        Returns:
            Problem: a copy of the problem with the added scalarization function.
        """
        if new_scal.symbol is None:
            new_scal.symbol = f"scal_{self._scalarization_index}"
            self._scalarization_index += 1

        if self.scalarization_funcs is None:
            return self.model_copy(update={"scalarization_funcs": [new_scal]})
        symbols = self.get_all_symbols()
        symbols.append(new_scal.symbol)
        symbol_counts = Counter(symbols)
        duplicates = {symbol: count for symbol, count in symbol_counts.items() if count > 1}

        if duplicates:
            msg = "Non-unique symbols found in the Problem model."
            for symbol, count in duplicates.items():
                msg += f" Symbol '{symbol}' occurs {count} times."

            raise ValueError(msg)

        return self.model_copy(update={"scalarization_funcs": [*self.scalarization_funcs, new_scal]})

    def add_constraints(self, new_constraints: list[Constraint]) -> "Problem":
        """Adds new constraints to the problem model.

        Does not modify the original problem model, but instead returns a copy of it with
        the added constraints. The symbols of the new constraints to be added must be
        unique.

        Args:
            new_constraints (list[Constraint]): the new `Constraint`s to be added to the model.

        Raises:
            TypeError: when the `new_constraints` is not a list.
            ValueError: when duplicate symbols are found among the new_constraints, or
                any of the new constraints utilized an existing symbol in the problem's model.

        Returns:
            Problem: a copy of the problem with the added constraints.
        """
        if not isinstance(new_constraints, list):
            # not a list
            msg = "The argument `new_constraints` must be a list."
            raise TypeError(msg)

        all_symbols = self.get_all_symbols()
        new_symbols = [const.symbol for const in new_constraints]

        if len(new_symbols) > len(set(new_symbols)):
            # duplicate symbols in the new constraint functions
            msg = "Duplicate symbols found in the new constraint functions to be added."
            raise ValueError(msg)

        for s in new_symbols:
            if s in all_symbols:
                # symbol already exists
                msg = "A symbol was provided for a new constraint that already exists in the problem definition."
                raise ValueError(msg)

        # proceed to add the new constraints
        return self.model_copy(
            update={
                "constraints": new_constraints if self.constraints is None else [*self.constraints, *new_constraints]
            }
        )

    def add_variables(self, new_variables: list[Variable | TensorVariable]) -> "Problem":
        """Adds new variables to the problem model.

        Does not modify the original problem model, but instead returns a copy of it with
        the added variables. The symbols of the new variables to be added must be
        unique.

        Args:
            new_variables (list[Variable | TensorVariable]): the new variables to be added to the model.

        Raises:
            TypeError: when the `new_variables` is not a list.
            ValueError: when duplicate symbols are found among the new_variables, or
                any of the new variables utilized an existing symbol in the problem's model.

        Returns:
            Problem: a copy of the problem with the added variables.
        """
        if not isinstance(new_variables, list):
            # not a list
            msg = "The argument `new_variables` must be a list."
            raise TypeError(msg)

        all_symbols = self.get_all_symbols()
        new_symbols = [const.symbol for const in new_variables]

        if len(new_symbols) > len(set(new_symbols)):
            # duplicate symbols in the new variables
            msg = "Duplicate symbols found in the new variables to be added."
            raise ValueError(msg)

        for s in new_symbols:
            if s in all_symbols:
                # symbol already exists
                msg = "A symbol was provided for a new variable that already exists in the problem definition."
                raise ValueError(msg)

        # proceed to add the new variables, assumed existing variables are defined
        return self.model_copy(update={"variables": [*self.variables, *new_variables]})

    def get_constraint(self, symbol: str) -> Constraint | None:
        """Return a copy of a `Constant` with the given symbol.

        Args:
            symbol (str): the symbol of the constraint.

        Returns:
            Constant | None: the copy of the constraint with the given symbol, or `None` if the constraint is not found.
                Also return `None` if no constraints have been defined for the problem.
        """
        if self.constraints is None:
            # no constraints defined
            return None
        for constraint in self.constraints:
            if constraint.symbol == symbol:
                return constraint.model_copy()

        # did not find symbol
        return None

    def get_variable(self, symbol: str) -> Variable | TensorVariable | None:
        """Return a copy of a `Variable` with the given symbol.

        Args:
            symbol (str): the symbol of the variable.

        Returns:
            Variable | TensorVariable | None: the copy of the variable with the given symbol,
                or `None` if the variable is not found.
        """
        for variable in self.variables:
            if variable.symbol == symbol:
                # variable found
                return variable.model_copy()

        # variable not found
        return None

    def get_objective(self, symbol: str) -> Objective | None:
        """Return a copy of an `Objective` with the given symbol.

        Args:
            symbol (str): the symbol of the objective.

        Returns:
            Objective | None: the copy of the objective with the given symbol, or `None` if the objective is not found.
        """
        for objective in self.objectives:
            if objective.symbol == symbol:
                # objective found
                return objective.model_copy()

        # objective not found
        return None

    def get_scalarization(self, symbol: str) -> ScalarizationFunction | None:
        """Return a copy of a `ScalarizationFunction` with the given symbol.

        Args:
            symbol (str): the symbol of the scalarization function.

        Returns:
            ScalarizationFunction | None: the copy of the scalarization function with the given symbol, or `None` if the
                scalarization function is not found. Returns `None` also when no scalarization functions have been
                defined for the problem.
        """
        if self.scalarization_funcs is None:
            # no scalarization functions defined
            return None

        for scal in self.scalarization_funcs:
            if scal.symbol == symbol:
                # scalarization function found
                return scal.model_copy()

        # scalarization function is not found
        return None

    def get_ideal_point(self) -> dict[str, float | None]:
        """Get the ideal point of the problem as an objective dict.

        Returns an objective dict containing the ideal values of the
        the problem for each objective function. These values may be `None`.

        Returns:
            dict[str, float | None] | None: an objective dict with the ideal
                point values (which may be `None`), or `None`.
        """
        return {f"{obj.symbol}": obj.ideal for obj in self.objectives}

    def get_nadir_point(self) -> dict[str, float | None]:
        """Get the nadir point of the problem as an objective dict.

        Returns an objective dict containing the nadir values of the
        the problem for each objective function. These values may be `None`.

        Returns:
            dict[str, float | None] | None: an objective dict with the nadir
                point values (which may be `None`), or `None`.
        """
        return {f"{obj.symbol}": obj.nadir for obj in self.objectives}

    @property
    def variable_domain(self) -> VariableDomainTypeEnum:
        """Check the variables defined for the problem and returns the type of their domain.

        Checks the variable types defined for the problem and tells if the
        problem is continuous, integer, binary, or mixed-integer.

        Returns:
            VariableDomainEnum: whether the problem is continuous, integer, binary, or mixed-integer.
        """
        variable_types = [var.variable_type for var in self.variables]

        if all(t == VariableTypeEnum.real for t in variable_types):
            # all variables are real valued -> continuous problem
            return VariableDomainTypeEnum.continuous

        if all(t in [VariableTypeEnum.integer, VariableTypeEnum.binary] for t in variable_types):
            # all variables are integer or binary -> integer problem
            return VariableDomainTypeEnum.integer

        # mixed problem
        return VariableDomainTypeEnum.mixed

    @property
    def is_convex(self) -> bool:
        """Check if all the functions expressions in the problem are convex.

        Note:
            This method just checks all the functions expressions present in the problem
            and return true if all of them are convex. For complicated problems, this might
            result in an incorrect results. User discretion is advised.

        Returns:
            bool: whether the problem is convex or not.
        """
        is_convex_values = (
            [obj.is_convex for obj in self.objectives]
            + ([con.is_convex for con in self.constraints] if self.constraints is not None else [])
            + ([extra.is_convex for extra in self.extra_funcs] if self.extra_funcs is not None else [])
            + ([scal.is_convex for scal in self.scalarization_funcs] if self.scalarization_funcs is not None else [])
        )

        return all(is_convex_values)

    @property
    def is_linear(self) -> bool:
        """Check if all the functions expressions in the problem are linear.

        Note:
            This method just checks all the functions expressions present in the problem
            and return true if all of them are linear. For complicated problems, this might
            result in an incorrect results. User discretion is advised.

        Returns:
            bool: whether the problem is linear or not.
        """
        is_linear_values = (
            [obj.is_linear for obj in self.objectives]
            + ([con.is_linear for con in self.constraints] if self.constraints is not None else [])
            + ([extra.is_linear for extra in self.extra_funcs] if self.extra_funcs is not None else [])
            + ([scal.is_linear for scal in self.scalarization_funcs] if self.scalarization_funcs is not None else [])
        )

        return all(is_linear_values)

    @property
    def is_twice_differentiable(self) -> bool:
        """Check if all the functions expressions in the problem are twice differentiable.

        Note:
            This method just checks all the functions expressions present in the problem
            and return true if all of them are twice differentiable. For complicated problems, this might
            result in an incorrect results. User discretion is advised.

        Returns:
            bool: whether the problem is twice differentiable or not.
        """
        is_diff_values = (
            [obj.is_twice_differentiable for obj in self.objectives]
            + ([con.is_twice_differentiable for con in self.constraints] if self.constraints is not None else [])
            + ([extra.is_twice_differentiable for extra in self.extra_funcs] if self.extra_funcs is not None else [])
            + (
                [scal.is_twice_differentiable for scal in self.scalarization_funcs]
                if self.scalarization_funcs is not None
                else []
            )
        )

        return all(is_diff_values)

    def get_scenario_problem(self, target_keys: str | list[str]) -> "Problem":
        """Returns a new Problem with fields belonging to a specified scenario.

        The new problem will have the fields `objectives`, `constraints`, `extra_funcs`,
        and `scalarization_funcs` with only the entries that belong to the specified
        scenario. The other entries will remain unchanged.

        Note:
            Fields with their `scenario_key` being `None` are assumed to belong to all scenarios,
            and are thus always included in each scenario.

        Args:
            target_keys (str | list[str]): the key or keys of the scenario(s) we wish to get.

        Raises:
            ValueError: (some of) the given `target_keys` has not been defined to be a scenario
                in the problem.

        Returns:
            Problem: a new problem with only the field that belong to the specified scenario.
        """
        if isinstance(target_keys, str):
            # if just a single key is given, make a list out of it.abs
            target_keys = [target_keys]

        # the any matches any keys
        if self.scenario_keys is None or not any(element in target_keys for element in self.scenario_keys):
            # invalid scenario
            msg = (
                f"The scenario '{target_keys}' has not been defined to be a valid scenario, or the problem has no "
                "scenarios defined."
            )
            raise ValueError(msg)

        # add the fields if the field has the given target_keys in its scenario_keys, or if the
        # target_keys is None
        scenario_objectives = [
            obj
            for obj in self.objectives
            if obj.scenario_keys is None or any(element in target_keys for element in obj.scenario_keys)
        ]
        scenario_constraints = (
            [
                cons
                for cons in self.constraints
                if cons.scenario_keys is None or any(element in target_keys for element in cons.scenario_keys)
            ]
            if self.constraints is not None
            else None
        )
        scenario_extras = (
            [
                extra
                for extra in self.extra_funcs
                if extra.scenario_keys is None or any(element in target_keys for element in extra.scenario_keys)
            ]
            if self.extra_funcs is not None
            else None
        )
        scenario_scals = (
            [
                scal
                for scal in self.scalarization_funcs
                if scal.scenario_keys is None or any(element in target_keys for element in scal.scenario_keys)
            ]
            if self.scalarization_funcs is not None
            else None
        )

        return self.model_copy(
            update={
                "objectives": scenario_objectives,
                "constraints": scenario_constraints,
                "extra_funcs": scenario_extras,
                "scalarization_funcs": scenario_scals,
            }
        )

    name: str = Field(
        description="Name of the problem.",
    )
    """Name of the problem."""
    description: str = Field(
        description="Description of the problem.",
    )
    """Description of the problem."""
    constants: list[Constant | TensorConstant] | None = Field(
        description="Optional list of the constants present in the problem.", default=None
    )
    """List of the constants present in the problem. Defaults to `None`."""
    variables: list[Variable | TensorVariable] = Field(
        description="List of variables present in the problem.",
    )
    """List of variables present in the problem."""
    objectives: list[Objective] = Field(
        description="List of the objectives present in the problem.",
    )
    """List of the objectives present in the problem."""
    constraints: list[Constraint] | None = Field(
        description="Optional list of constraints present in the problem.",
        default=None,
    )
    """Optional list of constraints present in the problem. Defaults to `None`."""
    extra_funcs: list[ExtraFunction] | None = Field(
        description="Optional list of extra functions. Use this if some function is repeated multiple times.",
        default=None,
    )
    """Optional list of extra functions. Use this if some function is repeated multiple times. Defaults to `None`."""
    scalarization_funcs: list[ScalarizationFunction] | None = Field(
        description="Optional list of scalarization functions of the problem.", default=None
    )
    """Optional list of scalarization functions of the problem. Defaults to `None`."""
    discrete_representation: DiscreteRepresentation | None = Field(
        description=(
            "Optional. Required when there are one or more 'data_based' Objectives. The corresponding values "
            "of the 'data_based' objective function will be fetched from this with the given variable values. "
            "Is also utilized for methods which require both an analytical and discrete representation of a problem."
        ),
        default=None,
    )
    """Optional. Required when there are one or more 'data_based' Objectives.
    The corresponding values of the 'data_based' objective function will be
    fetched from this with the given variable values.  Is also utilized for
    methods which require both an analytical and discrete representation of a
    problem. Defaults to `None`."""
    scenario_keys: list[str] | None = Field(
        description=(
            "Optional. The scenario keys defined for the problem. Each key will point to a subset of objectives, "
            "constraints, extra functions, and scalarization functions that have the same scenario key defined to them."
            "If None, then the problem is assumed to not contain scenarios."
        ),
        default=None,
    )
    """Optional. The scenario keys defined for the problem. Each key will point
    to a subset of objectives, " "constraints, extra functions, and
    scalarization functions that have the same scenario key defined to them."
    "If None, then the problem is assumed to not contain scenarios."""


if __name__ == "__main__":
    import erdantic as erd

    diagram = erd.create(Problem)
    diagram.draw("problem_map.png")

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

    problem_model = Problem(
        name="Example problem",
        description="This is an example of a the JSON object of the 'Problem' model.",
        constants=[constant_model],
        variables=[variable_model_1, variable_model_2, variable_model_3],
        objectives=[objective_model_1, objective_model_2, objective_model_3],
        constraints=[constraint_model],
        extra_funcs=[extra_func_model],
        scalarization_funcs=[scalarization_function_model],
    )

    # print(problem_model.model_dump_json(indent=2))
