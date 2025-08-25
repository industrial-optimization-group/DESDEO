"""Defines models for representing the state of various interactive methods."""

from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import object_session
from sqlalchemy.types import TypeDecorator
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    Session,
    SQLModel,
    select,
)

from desdeo.mcdm import ENautilusResult
from desdeo.tools import SolverResults

from .archive import UserSavedSolutionDB
from .preference import PreferenceType, ReferencePoint

if TYPE_CHECKING:
    from desdeo.tools.generics import EMOResults

    from .problem import ProblemDB, RepresentativeNonDominatedSolutions
    from .session import InteractiveSessionDB


class ResultsType(TypeDecorator):
    """SQLAlchemy custom type to convert a `SolverResults` and similar to JSON and back."""

    impl = JSON

    def process_bind_param(self, value, dialect):
        """`SolverResults` to JSON."""
        if value is None:
            return None

        if isinstance(value, list):
            return [x.model_dump() if hasattr(x, "model_dump") else x for x in value]

        if hasattr(value, "model_dump"):
            return value.model_dump()

        msg = f"No JSON serialization set for '{type(value)}'."
        print(msg)

        return value

    def process_result_value(self, value, dialect):
        """JSON to `SolverResults` or similar."""
        # Stupid way to to this, but works for now. Needs to add field
        # to the corresponding models so that they may be identified in dict form.
        if "closeness_measures" in value:  # noqa: SIM108
            model = ENautilusResult
        else:
            model = SolverResults

        if value is None:
            return None
        if isinstance(value, list):
            return [model.model_validate(x) for x in value]

        return model.model_validate(value)


class StateKind(str, Enum):
    """Stores the normalized kinds `{method}.{phase}` of supported states.

    Note:
        Update this when adding new states. Be sure to update `KIND_TO_STATE`
        in this file as well.
    """

    RPM_SOLVE = "reference_point_method.solve_candidates"
    NIMBUS_SOLVE = "nimbus.solve_candidates"
    NIMBUS_SAVE = "nimbus.save_solutions"
    NIMBUS_INIT = "nimbus.initialize"
    EMO_RUN = "emo.run"
    EMO_SAVE = "emo.save_solutions"
    GENERIC_INTERMEDIATE = "generic.solve_intermediate"
    ENAUTILUS_STEP = "e-nautilus.stepping"


class State(SQLModel, table=True):
    """The 'polymorphic' state to store method information."""

    __tablename__ = "states"

    id: int | None = Field(default=None, primary_key=True)

    # The state is polymorphic on these.
    # TODO (@gialmisi): once SQLModel supports polymorphic table types, refactor this.
    method: str = Field(index=True)  # the method name
    phase: str = Field(index=True)  # the phase of the method
    kind: StateKind = Field(index=True)  # normalized "{method}.{phase}", lowercase


class RPMState(SQLModel, table=True):
    """Reference Point Method (k+1 candidates)."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # inputs
    preferences: ReferencePoint = Field(sa_column=Column(PreferenceType))
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list[SolverResults] = Field(sa_column=Column(ResultsType))


class NIMBUSClassificationState(SQLModel, table=True):
    """NIMBUS: classification / solve candidates."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    current_objectives: dict[str, float] = Field(sa_column=Column(JSON), default_factory=dict)
    num_desired: int | None = 1
    previous_preference: "ReferencePoint | None" = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list["SolverResults"] = Field(sa_column=Column(JSON), default_factory=list)


class NIMBUSSaveState(SQLModel, table=True):
    """NIMBUS: save solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    solutions: list["UserSavedSolutionDB"] = Relationship(
        sa_relationship_kwargs={
            # tell SQLA which FK on the child points back to THIS parent
            "foreign_keys": lambda: [UserSavedSolutionDB.origin_state_id],
            "primaryjoin": lambda: NIMBUSSaveState.id == UserSavedSolutionDB.origin_state_id,
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        }
    )


class NIMBUSInitializationState(SQLModel, table=True):
    """NIMBUS: initialization."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    solver: str | None = None
    solver_results: list["SolverResults"] = Field(sa_column=Column(JSON), default_factory=list)


class EMOState(SQLModel, table=True):
    """EMO run (NSGA3, RVEA, etc.)."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    # algorithm flavor
    method_name: str = Field(description="Algorithm, e.g., NSGA3, RVEA")

    # parameters
    max_evaluations: int = Field(default=1000)
    number_of_vectors: int = Field(default=20)
    use_archive: bool = Field(default=True)

    # results
    solutions: list["EMOResults"] = Field(
        sa_column=Column(JSON), description="Optimization results", default_factory=list
    )
    outputs: list = Field(sa_column=Column(JSON), description="Optimization outputs", default_factory=list)


class EMOSaveState(SQLModel, table=True):
    """EMO: save solutions."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    problem_id: int

    # are these necessary here?
    max_evaluations: int = Field(default=1000)
    number_of_vectors: int = Field(default=20)
    use_archive: bool = Field(default=True)

    # results
    saved_solutions: list["EMOResults"] = Field(sa_column=Column(JSON), default_factory=list)
    solutions: list = Field(sa_column=Column(JSON), description="Original solutions from request", default_factory=list)


class IntermediateSolutionState(SQLModel, table=True):
    """Generic intermediate solutions requested by other methods."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    context: str | None = Field(
        default=None,
        description="Originating method context (e.g., 'nimbus', 'rpm') that requested these solutions",
    )
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = None
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    num_desired: int | None = 1
    reference_solution_1: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reference_solution_2: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)

    # results
    solver_results: list["SolverResults"] = Field(sa_column=Column(JSON), default_factory=list)


class ENautilusState(SQLModel, table=True):
    """E-NAUTILUS: one stepping iteration."""

    id: int | None = Field(default=None, primary_key=True, foreign_key="states.id")

    non_dominated_solutions_id: int | None = Field(foreign_key="representativenondominatedsolutions.id", default=None)

    current_iteration: int
    iterations_left: int
    selected_point: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    reachable_point_indices: list[int] = Field(sa_column=Column(JSON), default_factory=list)
    number_of_intermediate_points: int

    enautilus_results: "ENautilusResult" = Field(sa_column=Column(ResultsType))

    non_dominated_solutions: "RepresentativeNonDominatedSolutions" = Relationship()


class StateDB(SQLModel, table=True):
    """State holder with a single relationship to the base State."""

    __tablename__ = "statedb"

    id: int | None = Field(primary_key=True, default=None)

    # Optional cross-links (keep as strings in other modules to avoid circulars)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)
    session_id: int | None = Field(foreign_key="interactivesessiondb.id", default=None)

    # lineage
    parent_id: int | None = Field(foreign_key="statedb.id", default=None)

    # one-to-one to base state
    state_id: int | None = Field(foreign_key="states.id", default=None, index=True)
    base_state: State | None = Relationship(
        sa_relationship_kwargs={
            "uselist": False,
            "single_parent": True,
            "cascade": "all, delete-orphan",
            "foreign_keys": lambda: [StateDB.state_id],
        }
    )

    parent: "StateDB" = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": lambda: StateDB.id},
    )
    children: list["StateDB"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    session: "InteractiveSessionDB" = Relationship(back_populates="states")
    problem: "ProblemDB" = Relationship()

    @classmethod
    def create(
        cls,
        database_session: Session,
        *,
        problem_id: int | None = None,
        session_id: int | None = None,
        parent_id: int | None = None,
        state: SQLModel | None = None,
    ) -> "StateDB":
        """Build a StateDB + base State with a concrete substate."""
        sub_cls = type(state)
        kind: StateKind | None = None

        for cls_in_mro in sub_cls.mro():
            if cls_in_mro in SUBSTATE_TO_KIND:
                kind = SUBSTATE_TO_KIND[cls_in_mro]
                break

        if kind is None:
            raise ValueError(f"No StateKind mapping for substate type {sub_cls!r}")

        method, phase = _method_phase_from_kind(kind)
        base = State(method=method, phase=phase, kind=kind)

        row = cls(
            problem_id=problem_id,
            session_id=session_id,
            parent_id=parent_id,
            base_state=base,
        )
        database_session.add(row)

        # Persist base and link substate PK=FK
        attach_substate(database_session, base, state)

        return row

    @property
    def state(self) -> SQLModel | None:
        """Return the concrete substate instance (e.g., NIMBUSSaveState)...

        Return the concrete substate instance (e.g., NIMBUSSaveState)
        resolved from the stored `base_state`.
        """
        if self.base_state is None:
            return None
        table: SQLModel | None = KIND_TO_TABLE.get(self.base_state.kind)

        if table is None:
            return None

        db_session = object_session(self)

        if db_session is None:
            # No bound state
            raise RuntimeError("StateDB.state accessed without a bound Session")

        return db_session.exec(select(table).where(table.id == self.base_state.id)).first()


KIND_TO_TABLE: dict[StateKind, SQLModel] = {
    StateKind.RPM_SOLVE: RPMState,
    StateKind.NIMBUS_SOLVE: NIMBUSClassificationState,
    StateKind.NIMBUS_SAVE: NIMBUSSaveState,
    StateKind.NIMBUS_INIT: NIMBUSInitializationState,
    StateKind.EMO_RUN: EMOState,
    StateKind.EMO_SAVE: EMOSaveState,
    StateKind.GENERIC_INTERMEDIATE: IntermediateSolutionState,
    StateKind.ENAUTILUS_STEP: ENautilusState,
}

SUBSTATE_TO_KIND: dict[SQLModel, StateKind] = {
    RPMState: StateKind.RPM_SOLVE,
    NIMBUSClassificationState: StateKind.NIMBUS_SOLVE,
    NIMBUSSaveState: StateKind.NIMBUS_SAVE,
    NIMBUSInitializationState: StateKind.NIMBUS_INIT,
    EMOState: StateKind.EMO_RUN,
    EMOSaveState: StateKind.EMO_SAVE,
    IntermediateSolutionState: StateKind.GENERIC_INTERMEDIATE,
    ENautilusState: StateKind.ENAUTILUS_STEP,
}


def normalize_kind(method: str, phase: str) -> StateKind:
    """Normalize (method, phase) into a StateKind enum."""
    m = method.lower()
    p = phase.lower()

    if m in {"emo", "nsga3", "nsga-iii", "rvea"}:
        m = "emo"

    kind_str = f"{m}.{p}"
    return StateKind(kind_str)


def _method_phase_from_kind(kind: StateKind) -> tuple[str, str]:
    """Split enum value back to (method, phase)."""
    method, phase = kind.value.split(".", 1)
    return method, phase


def create_state(
    method: str,
    phase: str,
    *,
    payload: dict[str, Any] | None = None,
) -> tuple[State, SQLModel | None]:
    """Create base State and the proper concrete substate instance (if any)."""
    kind = normalize_kind(method, phase)
    base = State(method=method, phase=phase, kind=kind)
    table = KIND_TO_TABLE.get(kind)
    sub = table(**(payload or {})) if table else None
    return base, sub


def attach_substate(session, base: State, sub: SQLModel | None) -> None:
    """Persist base; link sub.id = base.id; persist sub."""
    session.add(base)
    session.flush()  # assigns base.id

    if sub is not None:
        sub.id = base.id
        session.add(sub)
        session.flush()


def load_concrete_state(session, base: State) -> SQLModel | None:
    """Given a base State row, load its concrete substate instance."""
    table = KIND_TO_TABLE.get(base.kind)

    if not table:
        return None

    return session.exec(select(table).where(table.id == base.id)).first()
