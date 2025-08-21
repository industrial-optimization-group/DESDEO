"""Defines models for representing the state of various interactive methods."""

from typing import TYPE_CHECKING

from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    SQLModel,
)

if TYPE_CHECKING:
    from desdeo.mcdm import ENautilusResult
    from desdeo.tools import SolverResults
    from desdeo.tools.generics import EMOResults

    from .archive import SolutionAddress, UserSavedSolutionDB
    from .preference import PreferenceDB, ReferencePoint
    from .problem import ProblemDB
    from .session import InteractiveSessionDB


class StateBase(SQLModel, table=True):
    """Base table for all states (polymorphic root)."""

    __tablename__ = "states"

    id: int | None = Field(default=None, primary_key=True)

    method: str = Field(index=True)
    phase: str = Field(index=True)

    kind: str = Field(
        index=True,
        description="Polymorphic discriminator, e.g., 'nimbus.solve_candidates'",
    )

    __mapper_args__ = {
        "polymorphic_on": "kind",
        "polymorphic_identity": "base",
    }


class RPMState(StateBase, table=True):
    """State of the reference point method for computing solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    phase: str = Field(default="solve_candidates", index=True)
    method: str = Field(default="reference_point_method", index=True)

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # solver_results: list[SolverResults] = Field(sa_column=Column(JSON))

    __mapper_args__ = {
        "polymorphic_identity": "reference_point_method.solve_candidates",
    }


class NIMBUSBaseState(StateBase):
    """Marker mixin for type hints only (no table)."""

    method: str = Field(default="nimbus", index=True)


class NIMBUSClassificationState(NIMBUSBaseState, table=True):
    """State of the NIMBUS method for computing solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    phase: str = Field(default="solve_candidates", index=True)

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    current_objectives: dict[str, float] = Field(sa_column=Column(JSON))
    num_desired: int | None = Field(default=1)
    # previous_preference: ReferencePoint = Field(sa_column=Column(JSON))

    # results
    # solver_results: list[SolverResults] = Field(sa_column=Column(JSON))

    __mapper_args__ = {
        "polymorphic_identity": "nimbus.solve_candidates",
    }


class NIMBUSSaveState(NIMBUSBaseState, table=True):
    """State of the NIMBUS method for saving solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    phase: str = Field(default="save_solutions", index=True)
    # solution_addresses: list[dict[str, Any]] = Field(sa_column=Column(JSON))

    __mapper_args__ = {
        "polymorphic_identity": "nimbus.save_solutions",
    }


class NIMBUSInitializationState(NIMBUSBaseState, table=True):
    """State of the NIMBUS method for initialization."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    phase: str = Field(default="initialize", index=True)
    solver: str | None = Field(default=None)
    # solver_results: list[SolverResults] = Field(sa_column=Column(JSON))

    __mapper_args__ = {
        "polymorphic_identity": "nimbus.initialize",
    }


class BaseEMOState(StateBase):
    """Common fields for EMO states (not a table)."""

    max_evaluations: int = Field(default=1000)
    number_of_vectors: int = Field(default=20)
    use_archive: bool = Field(default=True)


class EMOState(BaseEMOState, table=True):
    """State for EMO methods (execution/run)."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # The concrete algorithm flavor (NSGA3, RVEA, etc.) stays a column, not identity.
    method: str = Field(default="EMO", description="The EMO method family (e.g., EMO)")
    phase: str = Field(default="run", index=True)
    method_name: str = Field(description="Algorithm, e.g., NSGA3, RVEA")

    # results
    # solutions: list = Field(sa_column=Column(JSON), description="Optimization results")
    outputs: list = Field(sa_column=Column(JSON), description="Optimization outputs")

    __mapper_args__ = {
        "polymorphic_identity": "EMO.run",
    }


class EMOSaveState(BaseEMOState, table=True):
    """State of the EMO methods for saving solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    method: str = Field(default="EMO", description="The EMO method family (e.g., EMO)")
    phase: str = Field(default="save_solutions", index=True)
    problem_id: int
    # saved_solutions: list[EMOResults] = Field(sa_column=Column(JSON))
    solutions: list = Field(
        sa_column=Column(JSON),
        description="Original solutions from request",
        default_factory=list,
    )

    __mapper_args__ = {
        "polymorphic_identity": "EMO.save_solutions",
    }


class IntermediateSolutionState(StateBase, table=True):
    """State for computing intermediate solutions requested by other methods."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    phase: str = Field(default="solve_intermediate", index=True)
    method: str = Field(default="generic", index=True)

    context: str | None = Field(
        default=None,
        description="Originating method context (e.g., 'nimbus', 'rpm')",
    )
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    num_desired: int | None = Field(default=1)
    reference_solution_1: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reference_solution_2: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)

    # results
    # solver_results: list[SolverResults] = Field(sa_column=Column(JSON))

    __mapper_args__ = {
        "polymorphic_identity": "generic.solve_intermediate",
    }


class ENautilusState(StateBase, table=True):
    """State for the E-NAUTILUS method (one iteration/step)."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    method: str = Field(default="e-nautilus", index=True)
    phase: str = Field(default="stepping", index=True)

    # E-NAUTILUS (`e-nautilus_step`) specific
    non_dominated_points_id: int | None = Field(
        default=None,
        description=(
            "Stores the id of the `RepresentatvieNondominatedSolutions` in the DB. "
            "Use a service/repo layer to load the actual points."
        ),
    )
    current_iteration: int
    iterations_left: int
    selected_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reachable_point_indices: list[int] = Field(sa_column=Column(JSON), default_factory=list)
    number_of_intermediate_points: int

    # enautilus_results: ENautilusResult = Field(sa_column=Column(JSON))

    __mapper_args__ = {
        "polymorphic_identity": "e-nautilus.stepping",
    }


class StateDB(SQLModel, table=True):
    """Database model to store interactive method state."""

    id: int | None = Field(primary_key=True, default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)
    preference_id: int | None = Field(foreign_key="preferencedb.id", default=None)
    session_id: int | None = Field(foreign_key="interactivesessiondb.id", default=None)

    # Reference to other StateDB
    parent_id: int | None = Field(foreign_key="statedb.id", default=None)

    # NEW: One-to-one to the polymorphic hierarchy
    state_id: int | None = Field(foreign_key="states.id", default=None, index=True)

    state: "StateBase" = Relationship(
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "single_parent": True,
            "uselist": False,
            "foreign_keys": lambda: [StateDB.state_id],
        }
    )

    # Back populates
    session: "InteractiveSessionDB" = Relationship(back_populates="states")
    parent: "StateDB" = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": lambda: StateDB.id}
    )

    # if a parent node is killed, so are all its children (blood for the blood God)
    children: list["StateDB"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    saved_solutions: list["UserSavedSolutionDB"] | None = Relationship(
        back_populates="state", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Parents
    # preference: "PreferenceDB" = Relationship()
    # problem: "ProblemDB" = Relationship()
