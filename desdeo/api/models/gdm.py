"""Classes for group decision making"""

from sqlmodel import SQLModel, Field, Relationship, JSON, Column

from desdeo.api.models import User, ProblemDB, PreferenceBase
from desdeo.tools import SolverResults

class GroupBase(SQLModel):
    """Base class for group table model and group response model"""

class Group(GroupBase, table=True):
    """Table model for Group"""
    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(default=None)
    
    owner_id: int | None = Field(foreign_key="user.id", default=None)
    user_ids: list[int] | None = Field(sa_column=Column(JSON))
    
    problem_id: int = Field(default=None)

    head_iteration: "GroupIteration" = Relationship(back_populates="group")

class GroupPublic(GroupBase):
    """Response model for Group"""
    id: int
    name: str
    owner_id: int
    user_ids: list[int]
    problem_id: int

class GroupIteration(SQLModel, table=True):
    """Table model for Group Iteration"""
    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(default=None)
    
    group_id: int | None = Field(foreign_key="group.id", default=None)
    group: "Group" = Relationship(back_populates="head_iteration")
    
    set_preferences: dict[int, str] = Field(sa_column=Column(JSON)) # Dummy type
    results: str | None = Field(default=None) # Dummy type
    notified: dict[int, bool] = Field(sa_column=Column(JSON))

    parent_id: int | None = Field(foreign_key="groupiteration.id", default=None)
    parent: "GroupIteration" = Relationship(
        back_populates="child", 
        sa_relationship_kwargs={"remote_side": "GroupIteration.id"}
    )
    # If parent is removed, remove the child too
    child: "GroupIteration" = Relationship(
        back_populates="parent", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class GroupInfoRequest(SQLModel):
    group_id: int

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

