"""Defines models for archiving solutions."""

from typing import TYPE_CHECKING

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.tools.generics import EMOResults

from .state_table import StateDB

if TYPE_CHECKING:
    from .problem import ProblemDB
    from .user import User


class UserSavedEMOResults(EMOResults):
    """Defines a schema for storing emo solutions."""

    name: str | None = Field(
        description="An optional name for the solution, useful for archiving purposes.",
        default=None,
    )

    def to_emo_results(self) -> EMOResults:
        """Convert to SolverResults without the name field."""
        return EMOResults(
            optimal_variables=self.optimal_variables,
            optimal_objectives=self.optimal_objectives,
            constraint_values=self.constraint_values,
            extra_func_values=self.extra_func_values,
        )
