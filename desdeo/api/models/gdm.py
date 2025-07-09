"""Classes for group decision making"""

from sqlmodel import SQLModel, Field, Relationship, JSON, Column

from desdeo.api.models import User, PreferenceBase
from desdeo.tools import SolverResults

class Group(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    owner_id: int | None = Field(foreign_key="user.id", default=None)
    user_ids: list[int] | None = Field(sa_column=Column(JSON), default=None)
    problem_id: int | None = Field(default=None)
    name: str | None = Field(default=None)

class GroupIteration(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    parent_id: int | None = Field(foreign_key="groupiteration.id", default=None)
    child_id: int | None = Field(default=None, nullable=True)
    group_id: int | None = Field(foreign_key="group.id", default=None)
    preference_ids: list[int] | None = Field(sa_column=Column(JSON), default=None)
    problem_id: int | None = Field(default=None)

class GroupResult(SQLModel):
    solver_results: list[SolverResults]

class GroupAddRequest(SQLModel):
    group_id: int
    user_id: int

class GroupCreateRequest(SQLModel):
    group_name: str
    problem_id: int

class GroupAddRequest(SQLModel):
    group_id: int
    user_id: int