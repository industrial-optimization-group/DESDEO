"""Defines models for archiving solutions."""

from typing import TYPE_CHECKING

from sqlmodel import JSON, Column, Field, Relationship, SQLModel


if TYPE_CHECKING:
    from .problem import ProblemDB
    from .state import StateDB
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
    state_id: int | None = Field(foreign_key="statedb.id", default=None)
    # Back populates
    user: "User" = Relationship(back_populates="archive")
    problem: "ProblemDB" = Relationship(back_populates="solutions")
    state: "StateDB" = Relationship(back_populates="solutions")
