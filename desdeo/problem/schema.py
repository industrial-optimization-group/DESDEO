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

    longname: str = Field(
        description="Long descriptive name of the constant. This can be used in UI and visualizations.",
    )
    shortname: str = Field(
        description=(
            "Short name of the constant. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations."
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

    longname: str = Field(
        description="Long descriptive name of the variable. This can be used in UI and visualizations.",
    )
    shortname: str = Field(
        description=(
            "Short name of the variable. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations."
        ),
        max_length=MAX_SHORTNAME_LENGTH,
    )
    lowerbound: float | int | bool = Field(description="Lower bound of the variable.")
    upperbound: float | int | bool = Field(description="Upper bound of the variable.")
    variable_type: VariableTypes = Field(description="Type of the variable. Can be real, integer or binary.")
    initialvalue: float | int | bool | None = Field(
        description="Initial value of the variable. This is optional.",
    )


class ExtraFuncs(BaseModel):
    """Model for extra functions."""

    ...


class Objective(BaseModel):
    """Model for an objective."""

    longname: str = Field(
        description="Long descriptive name of the objective. This can be used in UI and visualizations.",
    )
    shortname: str = Field(
        description=(
            "Short name of the objective. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations."
        ),
        max_length=MAX_SHORTNAME_LENGTH,
    )
    func: list = Field(
        description=(
            "Function of the objective. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object. The symbols in the function must match variable/constant shortnames."
        ),
    )
    maximize: bool = Field(
        description="Whether the objective is to be maximized or minimized.",
        default=False,
    )
    ideal: float | None = Field(
        description="Ideal value of the objective. This is optional.",
    )  # Note: The examples use the term "lowerbound" instead of "ideal". That is a mistake.
    nadir: float | None = Field(
        description="Nadir value of the objective. This is optional.",
    )  # Note: The examples use the term "upperbound" instead of "nadir". That is a mistake.


class Constraint(BaseModel):
    """Model for a constraint."""

    longname: str = Field(
        description="Long descriptive name of the constraint. This can be used in UI and visualizations.",
    )
    shortname: str = Field(
        description=(
            "Short name of the constraint. This will be used in the rest of the problem definition."
            " It may also be used in UIs and visualizations."
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
    extra_funcs: list[ExtraFuncs] | None = Field(
        description="Optional list of extra functions. Use this if some function is repeated multiple times.",
    )


class DataObjective(Objective):
    """Model for a data-based objective definition."""

    func: list | None = Field(
        description=(
            "Optional analytical function of the objective. This is a JSON object that can be parsed into a function."
            "Must be a valid MathJSON object. The symbols in the function must match variable/constant shortnames."
        ),
    )


class DataProblem(BaseModel):
    """Model for a data-based problem definition."""

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
