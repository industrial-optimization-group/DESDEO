"""Classes for group decision making, aggregating all different types of data classes."""

import json

from sqlalchemy.types import TypeDecorator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.api.models.gdm.gdm_base import BaseGroupInfoContainer
from desdeo.api.models.gdm.gdm_score_bands import GDMSCOREBandFinalSelection, GDMSCOREBandInformation
from desdeo.api.models.gdm.gnimbus import EndProcessPreference, OptimizationPreference, VotingPreference
from desdeo.tools import SolverResults


class PreferenceType(TypeDecorator):
    """A converter of Preference types."""

    impl = JSON

    # Serialize
    def process_bind_param(self, value, dialect):
        """Turns a preference item into json."""
        if isinstance(value, BaseGroupInfoContainer):
            return value.model_dump_json()
        return None

    # Deserialize
    def process_result_value(self, value, dialect):
        """And the other way around."""
        jsoned = json.loads(value)
        if jsoned is not None:
            match jsoned["method"]:
                case "voting":
                    return VotingPreference.model_validate(jsoned)
                case "optimization":
                    return OptimizationPreference.model_validate(jsoned)
                # As the different methods are implemented, add new types
                case "end":
                    return EndProcessPreference.model_validate(jsoned)
                case "gdm-score-bands":
                    return GDMSCOREBandInformation.model_validate(jsoned)
                case "gdm-score-bands-final":
                    return GDMSCOREBandFinalSelection.model_validate(jsoned)
                case _:
                    print(f"Unable to deserialize Preference with method {jsoned['method']}.")
                    return None
        return None


class GroupBase(SQLModel):
    """Base class for group table model and group response model."""


class Group(GroupBase, table=True):
    """Table model for Group."""

    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(default=None)

    owner_id: int | None = Field(foreign_key="user.id", default=None)
    user_ids: list[int] | None = Field(sa_column=Column(JSON))

    problem_id: int = Field(default=None)

    """The id of the head GroupIteration."""
    head_iteration_id: int | None


class GroupPublic(GroupBase):
    """Response model for Group."""

    id: int
    name: str
    owner_id: int
    user_ids: list[int]
    problem_id: int


class GroupIteration(SQLModel, table=True):
    """Table model for Group Iteration (we could extend this in various ways)."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(default=None)

    """ID of the associated Group."""
    group_id: int

    """The preferences are stored in this item while the iteration is in progress."""
    info_container: BaseGroupInfoContainer = Field(sa_column=Column(PreferenceType))
    # NOTE: This used to be called "preferences" and the class used to be called "BasePreference"

    notified: dict[int, bool] = Field(sa_column=Column(JSON))

    """State for storing post optimization/voting related data (dec vars, objectives, etc.)"""
    state_id: int | None = Field()

    """Linked list emerges."""
    parent_id: int | None = Field(foreign_key="groupiteration.id", default=None)
    parent: "GroupIteration" = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "GroupIteration.id"}
    )
    # If parent is removed, remove the child too
    children: list["GroupIteration"] = Relationship(
        back_populates="parent", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class GroupInfoRequest(SQLModel):
    """Class for requesting group information."""

    group_id: int

class GroupRevertRequest(SQLModel):
    """Class for requesting reverting to certain iteration."""

    group_id: int = Field(description="The ID of the group we wish to revert.")
    state_id: int = Field(
        description="The state's ID to which we want to revert to. "\
            "Corresponds to state_id in GroupIteration."
    )


class GroupResult(SQLModel):
    """Class for group's result."""

    solver_results: list[SolverResults]


class GroupModifyRequest(SQLModel):
    """Used for adding a user into group and removing a user from group."""

    group_id: int
    user_id: int


class GroupCreateRequest(SQLModel):
    """Used for requesting a group to be created."""

    group_name: str
    problem_id: int
