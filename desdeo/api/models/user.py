"""Define models related to users."""

from enum import Enum

from sqlmodel import Field, SQLModel


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

    id: int = Field(primary_key=True, unique=True)
    password_hash: str = Field()
    role: UserRole = Field()
    group: str = Field(default="")


class UserPublic(UserBase):
    """The object to handle public user information."""

    id: int
    role: UserRole
    group: str
