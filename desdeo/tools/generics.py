"""Defines generic classes, functions, and objects utilized in the tools module."""
from pydantic import BaseModel, Field


class SolverError(Exception):
    """Raised when an error with a solver is encountered."""


class SolverResults(BaseModel):
    """Defines a schema for a dataclass to store the results of a solver."""

    optimal_variables: dict[str, float | list[float]] = Field(description="The optimal decision variables found.")
    optimal_objectives: dict[str, float | list[float]] = Field(
        description="The objective function values corresponding to the optimal decision variables found."
    )
    constraint_values: dict[str, float | list[float]] | None = Field(
        description=(
            "The constraint values of the problem. A negative value means the constraint is respected, "
            "a positive one means it has been breached."
        ),
        default=None,
    )
    success: bool = Field(description="A boolean flag indicating whether the optimization was successful or not.")
    message: str = Field(description="Description of the cause of termination.")
