"""GNIMBUS specific data classes; REMEMBER to add SER/DES into aggregator!"""

import json
from sqlmodel import Field, Column, JSON, TypeDecorator, SQLModel
from pydantic import ValidationError
from enum import Enum

from desdeo.api.models import (
    BasePreferences, 
    ReferencePointDictType, 
    ReferencePoint,
    SolutionReference
)
from desdeo.tools import SolverResults

class SolverResultType(TypeDecorator):
    """Not sure why the solver results wouldn't serialize but this should do the trick"""
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
        

class OptimizationPreference(BasePreferences):
    """An optimization preference class. As for the method and phase, see GNIMBUS for details."""

    method: str = "optimization"
    phase: str = Field(default="learning")
    set_preferences: dict[int, ReferencePoint] = Field(sa_column=Column(ReferencePointDictType))


class VotingPreference(BasePreferences):
    """Voting preferences"""
    method: str = "voting"
    set_preferences: dict[int, int] = Field(sa_column=Column(JSON)) # A user votes for an index from the results (or something)


class GNIMBUSResultResponse(SQLModel):
    """The response for getting GNIMBUS results"""
    method: str
    phase: str
    preferences: VotingPreference | OptimizationPreference
    common_results: list[SolutionReference]
    user_results: list[SolutionReference]
    personal_result_index: int | None

class FullIteration(SQLModel):
    phase: str
    optimization_preferences: OptimizationPreference
    voting_preferences: VotingPreference | None
    starting_result: SolutionReference
    common_results: list[SolutionReference]
    user_results: list[SolutionReference]
    final_result: SolutionReference | None

class GNIMBUSAllIterationsResponse(SQLModel):
    """The response model for getting all found solutions among others"""
    all_full_iterations: list[FullIteration]