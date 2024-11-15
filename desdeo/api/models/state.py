"""Defines models for representing the state of various interactive methods."""

from typing import Literal

from sqlalchemy.types import TypeDecorator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.tools import SolverResults

from .preference import PreferenceDB
from .problem import ProblemDB
from .session import InteractiveSessionDB


class StateType(TypeDecorator):
    """SQLAlchemy custom type to convert states to JSON and back."""

    impl = JSON

    def process_bind_param(self, value, dialect):
        """State to JSON."""
        if isinstance(value, RPMState):
            return value.model_dump()

        msg = f"No JSON serialization set for ste of type '{type(value)}'."
        print(msg)

        return value

    def process_result_value(self, value, dialect):
        """JSON to state."""
        if "method" in value:
            match value["method"]:
                case "reference_point_method":
                    return RPMState.model_validate(value)
                case _:
                    msg = f"No method '{value["method"]}' found."
                    print(msg)

        return value


class BaseState(SQLModel):
    """The base model for representing method state."""

    method: Literal["unset"] = "unset"


class RPMBaseState(BaseState):
    """."""

    phase: Literal["solve_candidates"] = "solve_candidates"


class RPMState(RPMBaseState):
    """State for the reference point method."""

    method: Literal["reference_point_method"] = "reference_point_method"

    # to compute k+1 solutions
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(JSON))


class StateDB(SQLModel, table=True):
    """Database model to store interactive method state."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)
    preference_id: int | None = Field(foreign_key="preferencedb.id", default=None)
    session_id: int | None = Field(foreign_key="interactivesessiondb.id", default=None)

    # Reference to other StateDB
    parent_id: int | None = Field(foreign_key="statedb.id", default=None)

    state: BaseState | None = Field(sa_column=Column(StateType), default=None)

    # Back populates
    session: "InteractiveSessionDB" = Relationship(back_populates="states")
    parent: "StateDB" = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "StateDB.id"})
    # if a parent node is killed, so are all its children (blood for the blood God)
    children: list["StateDB"] = Relationship(
        back_populates="parent", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Parents
    preference: "PreferenceDB" = Relationship()
    problem: "ProblemDB" = Relationship()
