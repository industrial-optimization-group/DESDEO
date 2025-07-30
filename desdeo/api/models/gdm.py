"""Classes for group decision making"""

import json

from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from pydantic import ValidationError

from desdeo.api.models import ReferencePoint
from desdeo.tools import SolverResults

class SolverResultType(TypeDecorator):
    """Dunno why the solver results wouldn't serialize but this should do the trick"""
    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, list):
            solver_list = []
            for item in value:
                if isinstance(item, SolverResults):
                    solver_list.append(item.model_dump_json())
            return json.dumps(solver_list)
    
    def process_result_value(self, value, dialect):
        if value is not None:
            value_list = json.loads(value)
            solver_list: SolverResults = []
            for item in value_list:
                item_dict = json.loads(item)
                try:
                    solver_list.append(SolverResults.model_validate(item_dict))
                except ValidationError as e:
                    print(f"Validation error when deserializing SolverResults: {e}")
                    continue
            return solver_list
        
class ReferencePointDictType(TypeDecorator):
    """A converter for dict of int and preferences"""
    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, ReferencePoint):
                    value[key] = item.model_dump_json()
            return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        dictionary = json.loads(value)
        for key, item in dictionary.items():
            if item == None:
                print("Something's wrong... Database has a NoneType entry.")
            try:
                dictionary[key] = ReferencePoint.model_validate(json.loads(item))
            except ValidationError as e:
                print(f"Validation error when deserializing PreferencePoint: {e}")
        return dictionary
        

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
    
    set_preferences: dict[int, ReferencePoint] = Field(sa_column=Column(ReferencePointDictType)) # (ERIKOISTA)
    results: list[SolverResults] = Field(sa_column=Column(SolverResultType)) # (ERIKOISTA)
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

