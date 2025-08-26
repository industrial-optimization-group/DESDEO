"""Defines models for representing the state of various interactive methods."""

from typing import Literal

from sqlalchemy.types import TypeDecorator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.mcdm import ENautilusResult
from desdeo.tools import SolverResults
from desdeo.tools.generics import EMOResults

from .archive import SolutionAddress, UserSavedSolutionDB
from .preference import PreferenceDB, ReferencePoint
from .problem import ProblemDB
from .session import InteractiveSessionDB


class StateType(TypeDecorator):
    """SQLAlchemy custom type to convert states to JSON and back."""

    impl = JSON

    def process_bind_param(self, value, dialect):
        """State to JSON."""
        if isinstance(
            value,
            RPMState
            | NIMBUSClassificationState
            | IntermediateSolutionState
            | NIMBUSSaveState
            | EMOState
            | EMOSaveState
            | NIMBUSInitializationState
            | ENautilusState,
        ):
            return value.model_dump()

        msg = f"No JSON serialization set for ste of type '{type(value)}'."
        print(msg)

        return value

    def process_result_value(self, value, dialect):  # noqa: PLR0911
        """JSON to state."""
        if "method" in value:
            match (value["method"], value.get("phase")):
                case ("reference_point_method", _):
                    return RPMState.model_validate(value)
                case ("nimbus", "solve_candidates"):
                    return NIMBUSClassificationState.model_validate(value)
                case ("nimbus", "initialize"):
                    return NIMBUSInitializationState.model_validate(value)
                case ("nimbus", "save_solutions"):
                    return NIMBUSSaveState.model_validate(value)
                case ("generic", _):
                    return IntermediateSolutionState.model_validate(value)
                case (method, "save_solutions") if method in [
                    "NSGA3",  # Changed from NSGAIII to match EMO router output
                    "RVEA",
                    "EMO",
                ]:
                    return EMOSaveState.model_validate(value)
                case (method, _) if method in [
                    "NSGA3",
                    "RVEA",
                    "EMO",
                ]:  # Changed from NSGAIII to NSGA3
                    return EMOState.model_validate(value)
                case ("e-nautilus", "stepping"):
                    return ENautilusState.model_validate(value)
                case _:
                    msg = f"No method '{value['method']}' with phase '{value.get('phase')}' found."
                    print(msg)

        return value


class BaseState(SQLModel):
    """The base model for representing method state."""

    method: Literal["unset"] = "unset"
    phase: Literal["unset"] = "unset"


class BaseEMOState(BaseState):
    """The base state for EMO methods."""

    max_evaluations: int = Field(default=1000)
    number_of_vectors: int = Field(default=20)
    use_archive: bool = Field(default=True)


class RPMBaseState(BaseState):
    """The base sate for the reference point method (RPM).

    Other states of the RPM should inherit from this.
    """

    method: Literal["reference_point_method"] = "reference_point_method"


class RPMState(RPMBaseState):
    """State of the reference point method for computing solutions."""

    phase: Literal["solve_candidates"] = "solve_candidates"

    # to compute k+1 solutions
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(JSON))


class NIMBUSBaseState(BaseState):
    """The base sate for the reference point method (NIMBUS).

    Other states of the NIMBUS should inherit from this.
    """

    method: Literal["nimbus"] = "nimbus"


class NIMBUSClassificationState(NIMBUSBaseState):
    """State of the nimbus method for computing solutions."""

    phase: Literal["solve_candidates"] = "solve_candidates"

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    current_objectives: dict[str, float] = Field(sa_column=Column(JSON))
    num_desired: int | None = Field(default=1)
    previous_preference: ReferencePoint = Field(Column(JSON))

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(JSON))


class NIMBUSSaveState(NIMBUSBaseState):
    """State of the nimbus method for saving solutions."""

    phase: Literal["save_solutions"] = "save_solutions"
    solution_addresses: list[SolutionAddress] = Field(sa_column=Column(JSON))


class EMOState(BaseEMOState):
    """State for EMO methods."""

    method: str = Field(default="EMO", description="The EMO method name (e.g., NSGA3, RVEA, etc.)")

    # results
    solutions: list = Field(sa_column=Column(JSON), description="Optimization results")
    outputs: list = Field(sa_column=Column(JSON), description="Optimization results")


class EMOSaveState(BaseEMOState):
    """State of the EMO methods for saving solutions."""

    method: str = Field(default="EMO", description="The EMO method name (e.g., NSGA3, RVEA, etc.)")
    phase: Literal["save_solutions"] = "save_solutions"
    problem_id: int
    saved_solutions: list[EMOResults] = Field(sa_column=Column(JSON))
    solutions: list = Field(
        sa_column=Column(JSON),
        description="Original solutions from request",
        default_factory=list,
    )


class NIMBUSInitializationState(NIMBUSBaseState):
    """State of the nimbus method for computing solutions."""

    phase: Literal["initialize"] = "initialize"
    solver: str | None = Field(default=None)
    solver_results: list[SolverResults] = Field(sa_column=Column(JSON))


class IntermediateSolutionState(BaseState):
    """State of the nimbus method for computing solutions."""

    method: Literal["generic"] = "generic"
    phase: Literal["solve_intermediate"] = "solve_intermediate"
    context: str = Field(
        default=None,
        description="The originating method context (e.g., 'nimbus', 'rpm') that requested these solutions",
    )
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    num_desired: int | None = Field(default=1)
    reference_solution_1: dict[str, float]
    reference_solution_2: dict[str, float]
    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(JSON))


class ENautilusState(BaseState):
    """State for the E-NAUTILUS method.

    This state represents a step (iteration) in the E-NAUTILUS method.
    """

    method: Literal["e-nautilus"] = "e-nautilus"
    phase: Literal["stepping"] = "stepping"

    # E-NAUTILUS (`e-nautilus_step`) specific
    non_dominated_points_id: int | None = Field(
        description=(
            "Stores the id of the `RepresentatvieNondominatedSolutions` in the DB. "
            "Use the property `non_dominated_points` to get the actual points."
        )
    )
    current_iteration: int
    iterations_left: int
    selected_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reachable_point_indices: list[int]
    number_of_intermediate_points: int

    enautilus_results: ENautilusResult = Field(sa_column=Column(JSON))


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
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    saved_solutions: list["UserSavedSolutionDB"] | None = Relationship(
        back_populates="state", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    # Parents
    preference: "PreferenceDB" = Relationship()
    problem: "ProblemDB" = Relationship()
