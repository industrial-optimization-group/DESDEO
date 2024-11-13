"""Defines user models."""

from enum import Enum
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from .preference import PreferenceDB

if TYPE_CHECKING:
    from .archive import ArchiveEntryDB
    from .schemas import ProblemDB


class UserRole(str, Enum):
    """Possible user roles."""

    guest = "guest"
    dm = "dm"
    analyst = "analyst"
    admin = "admin"


class UserBase(SQLModel):
    """Base user object."""

    username: str = Field(index=True)


class User(UserBase, table=True):
    """The table model of the user stored in the database."""

    id: int | None = Field(primary_key=True, default=None)
    password_hash: str = Field()
    role: UserRole = Field()
    group: str = Field(default="")

    # Back populates
    archive: list["ArchiveEntryDB"] = Relationship(back_populates="user")
    preferences: list["PreferenceDB"] = Relationship(back_populates="user")
    problems: list["ProblemDB"] = Relationship(back_populates="user")


class UserPublic(UserBase):
    """The object to handle public user information."""

    id: int
    role: UserRole
    group: str
