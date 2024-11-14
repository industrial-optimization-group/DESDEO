"""Defines Session models to manage user sessions."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .state import StateDB


class InteractiveSessionBase(SQLModel):
    """The base model for representing interactive sessions."""


class InteractiveSessionDB(SQLModel, table=True):
    """Database model to store sessions."""

    id: int | None = Field(primary_key=True, default=None)
    user_id: int | None = Field(foreign_key="user.id", default=None)

    # Back populates
    states: list["StateDB"] = Relationship(back_populates="session")
