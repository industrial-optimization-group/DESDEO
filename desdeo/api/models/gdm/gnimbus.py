"""GNIMBUS specific data classes; REMEMBER to add SER/DES into aggregator!"""

import json

from pydantic import ValidationError
from sqlmodel import JSON, Column, Field, SQLModel, TypeDecorator

from desdeo.api.models.gdm.gdm_base import (
    BasePreferences,
    BooleanDictTypeDecorator,
    ReferencePoint,
    ReferencePointDictType,
)
from desdeo.api.models.generic_states import SolutionReference
from desdeo.tools import SolverResults


class SolverResultType(TypeDecorator):
    """Not sure why the solver results wouldn't serialize but this should do the trick."""

    impl = JSON

    def process_bind_param(self, value, dialect):
        if isinstance(value, list):
            solver_list = []
            for item in value:
                if isinstance(item, SolverResults):
                    solver_list.append(item.model_dump_json())
            return json.dumps(solver_list)
        return None

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
        return None


class GNIMBUSSwitchPhaseRequest(SQLModel):
    """A request for a certain phase. Comes from the group owner/analyst."""

    group_id: int
    new_phase: str


class GNIMBUSSwitchPhaseResponse(SQLModel):
    """A response for the above request."""

    old_phase: str
    new_phase: str


class OptimizationPreference(BasePreferences):
    """An optimization preference class. As for the method and phase, see GNIMBUS for details."""

    method: str = "optimization"
    phase: str = Field(default="learning")
    set_preferences: dict[int, ReferencePoint] = Field(sa_column=Column(ReferencePointDictType))


class VotingPreference(BasePreferences):
    """Voting preferences."""

    method: str = "voting"
    set_preferences: dict[int, int] = Field(
        sa_column=Column(JSON)
    )  # A user votes for an index from the results (or something)


class EndProcessPreference(BasePreferences):
    """A model for determining if everyone is happy with current solution so we can end the process."""

    method: str = "end"
    success: bool | None = Field()

    # We check if everyone agrees to stop.
    set_preferences: dict[int, bool] = Field(sa_column=Column(BooleanDictTypeDecorator))


class GNIMBUSResultResponse(SQLModel):
    """The response for getting GNIMBUS results."""

    method: str
    phase: str
    preferences: VotingPreference | OptimizationPreference
    common_results: list[SolutionReference]
    user_results: list[SolutionReference]
    personal_result_index: int | None


class FullIteration(SQLModel):
    """A full iteration item containing results from a complete or incomplete iteration."""

    phase: str
    optimization_preferences: OptimizationPreference | None
    voting_preferences: VotingPreference | EndProcessPreference | None
    starting_result: SolutionReference | None
    common_results: list[SolutionReference]
    user_results: list[SolutionReference]
    personal_result_index: int | None
    final_result: SolutionReference | None


class GNIMBUSAllIterationsResponse(SQLModel):
    """The response model for getting all found solutions among others."""

    all_full_iterations: list[FullIteration]
