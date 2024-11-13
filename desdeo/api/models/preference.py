"""Defines a models for representing preferences."""

from typing import TYPE_CHECKING

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from .problem import ProblemDB

if TYPE_CHECKING:
    from .archive import ArchiveEntryDB
    from .user import User


class PreferenceBase(SQLModel):
    """The base model for representing preferences."""


class ReferencePoint(PreferenceBase):
    """Model for representing a reference point type of preference."""

    aspiration_levels: dict[str, float] = Field(sa_column=Column(JSON, nullable=False))


class PreferenceDB(PreferenceBase, table=True):
    """Database model for storing preferences."""

    id: int | None = Field(primary_key=True, default=None)
    user_id: int | None = Field(foreign_key="user.id", default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)

    # Back populates
    problem: "ProblemDB" = Relationship(back_populates="preferences")
    user: "User" = Relationship(back_populates="preferences")
    solutions: list["ArchiveEntryDB"] = Relationship(back_populates="preference")
