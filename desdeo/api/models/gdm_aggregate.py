"""Classes for group decision making, aggregating all different types of data classes 
from across the derived classes of BaseSolverResult
"""

import json

from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel, Field, Relationship, JSON, Column

from desdeo.api.models import BasePreferences, StateDB
from desdeo.api.models.gnimbus import (
    VotingPreference,
    OptimizationPreference
)
from desdeo.tools import SolverResults

class PreferenceType(TypeDecorator):
    """A converter of Preference/Result types"""

    impl = JSON

    # Serialize
    def process_bind_param(self, value, dialect):
        if isinstance(value, BasePreferences):
            valmd = value.model_dump_json()
            return valmd
        return None
            
    # Deserialize
    def process_result_value(self, value, dialect):
        jsoned = json.loads(value)
        if jsoned is not None:
            match jsoned["method"]:
                case "voting":
                    valdeser = VotingPreference.model_validate(jsoned)
                    return valdeser
                case "optimization":
                    valdeser = OptimizationPreference.model_validate(jsoned)
                    return valdeser
                # As the different methods are implemented, add new types
                case _:
                    print(f"Unable to deserialize PreferenceResult with method {jsoned["method"]}.")
                    return None
        return None

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
    """Table model for Group Iteration (we could extend this in various ways)"""
    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(default=None)
    
    group_id: int | None = Field(foreign_key="group.id", default=None)
    group: "Group" = Relationship(back_populates="head_iteration")
    
    # Preferences that are filled as they come (remove the RESULT aspect from this, just put the results to the state.)
    preferences: BasePreferences = Field(sa_column=Column(PreferenceType))
    notified: dict[int, bool] = Field(sa_column=Column(JSON))

    # TODO: Add a state db item to contain the results. This should allow e.g. UTOPIA endpoints to function.
    # I don't want a relation to StateDB so I feel this might be the way to do that
    state_id: int | None = Field()

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

