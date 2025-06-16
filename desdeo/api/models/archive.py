"""Defines models for archiving solutions."""

from typing import TYPE_CHECKING

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.tools.generics import SolverResults

if TYPE_CHECKING:
    from .problem import ProblemDB
    from .user import User


class UserSavedSolutionBase(SQLModel):
    """The base model of an archive entry."""

    variable_values: dict[str, float | list] = Field(sa_column=Column(JSON, nullable=False))
    objective_values: dict[str, float] = Field(sa_column=Column(JSON, nullable=False))
    constraint_values: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    extra_func_values: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)

class UserSavedSolutionDB(UserSavedSolutionBase, table=True):
    """Database model of an archive entry."""

    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(default=None, nullable=True)  # Optional name for the solution
    user_id: int | None = Field(foreign_key="user.id", default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)
    # Back populates
    user: "User" = Relationship(back_populates="archive")
    problem: "ProblemDB" = Relationship(back_populates="solutions")

class UserSavedSolverResults(SolverResults):
    """Defines a schema for storing archived solutions."""
    name: str | None = Field(
        description="An optional name for the solution, useful for archiving purposes.", default=None
    )

    def to_solver_results(self) -> SolverResults:
        """Convert to SolverResults without the name field."""
        return SolverResults(
            optimal_variables=self.optimal_variables,
            optimal_objectives=self.optimal_objectives,
            constraint_values=self.constraint_values,
            extra_func_values=self.extra_func_values,
            scalarization_values=self.scalarization_values,
            success=self.success,
            message=self.message,
        )