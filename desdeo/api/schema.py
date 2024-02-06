"""Pydantic schemas for the API."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class UserRole(Enum):
    """Enum of user roles."""

    GUEST = "guest"
    DM = "dm"
    ANALYST = "analyst"


class User(BaseModel):
    """Model for a user. Temporary."""

    username: str = Field(description="Username of the user.")
    password_hash: str = Field(description="SHA256 Hash of the user's password.")
    problems: list[str] = Field(description="List of problem names the user has access to.")
    role: UserRole = Field(description="Role of the user.")
    user_group: str = Field(description="User group of the user. Used for group decision making.")
    # To allows for User to be initialized from database instead of just dicts.
    model_config = ConfigDict(from_attributes=True)
