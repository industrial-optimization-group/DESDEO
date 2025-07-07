"""Classes for group decision making"""

from sqlmodel import SQLModel, Field, Relationship, JSON, Column

from desdeo.api.models import User, PreferenceBase
from desdeo.tools import SolverResults

class Group(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    user_ids: list[int] | None = Field(sa_column=Column(JSON), default=None)
    name: str | None = Field(default=None)

class GroupIteration(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    parent_id: int | None = Field(default=None)
    group_id: int | None = Field(default=None)

class GroupResult(SQLModel):
    solver_results: list[SolverResults]

class GroupSessionJoinRequest(SQLModel):
    group_id: int