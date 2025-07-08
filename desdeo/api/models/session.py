"""Defines Session models to manage user sessions."""

from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .state import StateDB
    from .user import User


class CreateSessionRequest(SQLModel):
    """Model of the request to create a new session."""

    info: str | None = Field(default=None)


class GetSessionRequest(SQLModel):
    """Model of the request to get a specific session."""

    session_id: int = Field()


class InteractiveSessionBase(SQLModel):
    """The base model for representing interactive sessions."""

    id: int | None
    user_id: int | None

    info: str | None


InteractiveSessionInfo = InteractiveSessionBase


class InteractiveSessionDB(InteractiveSessionBase, table=True):
    """Database model to store sessions."""

    id: int | None = Field(primary_key=True, default=None)
    user_id: int | None = Field(foreign_key="user.id", default=None)

    info: str | None = Field(default=None)

    # Back populates
    states: list["StateDB"] = Relationship(back_populates="session")
    user: "User" = Relationship(back_populates="sessions")
