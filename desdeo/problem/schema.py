"""Schema for the problem definition.

The problem definition is a JSON file that contains the following information:

- Constants
- Variables
- Objectives
- Extra functions

"""

from enum import Enum

import polars as pl
from pydantic import BaseModel, Field

MAX_SHORTNAME_LENGTH = 3


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
        max_length=MAX_SHORTNAME_LENGTH,
    )
    value: float | int | bool = Field(description="Value of the constant.")


class VariableTypes(Enum):
    """Enum of variable types."""

    real = "real"
    integer = "integer"
    binary = "binary"


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
        max_length=MAX_SHORTNAME_LENGTH,
    )
    lowerbound: float | int | bool = Field(description="Lower bound of the variable.")
    upperbound: float | int | bool = Field(description="Upper bound of the variable.")
    variable_type: VariableTypes = Field(description="Type of the variable. Can be real, integer or binary.")
    initialvalue: float | int | bool | None = Field(
        description="Initial value of the variable. This is optional.",
    )


class ExtraFunction(BaseModel):
    """Model for extra functions."""

    ...


class ScalarizationFunction(BaseModel):
    """Model for scalarization of the problem."""

    ...


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
        max_length=MAX_SHORTNAME_LENGTH,
    )
    func: list = Field(
        description=(
            "The objective function. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object. The symbols in the function must match variable/constant shortnames."
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
    shortname: str = Field(
        description=(
            "Symbol to represent the constraint. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations. Example: 'g_1'."
        ),
        max_length=MAX_SHORTNAME_LENGTH,
    )
    func: list = Field(
        description=(
            "Function of the constraint. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object."
            " The symbols in the function must match objective/variable/constant shortnames."
        ),
    )


class EvaluatedPoint(BaseModel):
    """Model to represent the evaluated objective values of an decision vector."""

    ...


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
