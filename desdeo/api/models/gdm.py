"""Classes for group decision making"""

from sqlmodel import SQLModel, Field, Relationship, JSON, Column

from desdeo.api.models import User, ProblemDB, PreferenceBase
from desdeo.tools import SolverResults

class Group(SQLModel, table=True):
    """Table model for Group"""
    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(default=None)
    
    owner_id: int | None = Field(foreign_key="user.id", default=None)
    user_ids: list[int] | None = Field(sa_column=Column(JSON))
    
    problem_id: int = Field(default=None)

    group_iterations: list["GroupIteration"] | None = Relationship(back_populates="group")


class GroupIteration(SQLModel, table=True):
    """Table model for Group Iteration"""
    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(default=None)
    
    group_id: int | None = Field(foreign_key="group.id", default=None)
    group: "Group" = Relationship(back_populates="group_iterations")
    
    set_preferences: dict[int, str] = Field(sa_column=Column(JSON))

    parent_id: int | None = Field(foreign_key="groupiteration.id", default=None)
    parent: "GroupIteration" = Relationship(
        back_populates="child", 
        sa_relationship_kwargs={"remote_side": "GroupIteration.id"}
    )

    child: "GroupIteration" = Relationship(back_populates="parent")


class GroupResult(SQLModel):
    solver_results: list[SolverResults]

class GroupModifyRequest(SQLModel):
    """Used for adding a user into group and removing a user from group"""
    group_id: int
    user_id: int

class GroupCreateRequest(SQLModel):
    """Used for requesting a group to be created"""
    group_name: str
    problem_id: int

