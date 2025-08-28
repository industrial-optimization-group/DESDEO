"""Defines models for representing the state of various interactive methods."""

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, computed_field
from sqlalchemy.orm import object_session
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    Session,
    SQLModel,
    select,
)

from desdeo.problem import VariableType

from .state import (
    EMOSaveState,
    EMOState,
    ENautilusState,
    IntermediateSolutionState,
    NIMBUSClassificationState,
    NIMBUSInitializationState,
    NIMBUSSaveState,
    RPMState,
)
from .user import User

if TYPE_CHECKING:
    from .problem import ProblemDB
    from .session import InteractiveSessionDB


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


class UserSavedSolutionDB(SQLModel, table=True):
    """Database model of an archived solution."""

    id: int | None = Field(primary_key=True, default=None)

    name: str | None = Field(default=None, nullable=True)
    objective_values: dict[str, float] = Field(sa_column=Column(JSON))
    variable_values: dict[str, VariableType] = Field(sa_column=Column(JSON))
    solution_index: int | None

    # Links
    user_id: int | None = Field(foreign_key="user.id", default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)
    origin_state_id: int | None = Field(foreign_key="states.id", default=None)  # the StateDB holder

    # Back populates
    user: "User" = Relationship(back_populates="archive")
    problem: "ProblemDB" = Relationship(back_populates="solutions")

    @classmethod
    def from_state_info(
        cls,
        database_session: Session,
        user_id: int,
        problem_id: int,
        state_id: int,
        solution_index: int,
        name: str | None,
    ) -> "UserSavedSolutionDB | None":
        state = database_session.exec(
            select(StateDB).where(
                StateDB.id == state_id,
                StateDB.problem_id == problem_id,
            )
        ).first()

        if state is None:
            return None

        objective_values = state.state.result_objective_values[solution_index]
        variable_values = state.state.result_variable_values[solution_index]

        return cls(
            name=name,
            objective_values=objective_values,
            variable_values=variable_values,
            solution_index=solution_index,
            user_id=user_id,
            problem_id=problem_id,
            origin_state_id=state_id,
        )


class SolutionAddress(SQLModel):
    # objective_values: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)
    # address_state: int | None = Field(sa_column=Column(JSON), default=None)
    # address_result: int | None = Field(sa_column=Column(JSON), default=None)

    name: str | None = Field(description="Optional name to help identify the solution if, e.g., saved.", default=None)
    solution_index: int | None = Field(
        description="The index of the referenced solution, if multiple solutions exist in the reference state.",
        default=None,
    )
    state: StateDB = Field(description="The reference state with the solution information.")

    @computed_field
    @property
    def objective_values_all(self) -> list[dict[str, float]]:
        return self.state.state.result_objective_values

    @computed_field
    @property
    def variable_values_all(self) -> list[dict[str, VariableType]]:
        return self.state.state.result_objective_values

    @computed_field
    @property
    def objective_values(self) -> dict[str, float] | None:
        if self.solution_index is not None:
            return self.state.state.result_objective_values[self.solution_index]

        return None

    @computed_field
    @property
    def variable_values(self) -> dict[str, VariableType] | None:
        if self.solution_index is not None:
            return self.state.state.result_variable_values[self.solution_index]

        return None

    @computed_field
    @property
    def state_id(self) -> int:
        return self.state.id

    @computed_field
    @property
    def num_solutions(self) -> int:
        return len(self.state.state.solver_results)


class SolutionAddressResponse(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None
    solution_index: int | None
    state_id: int
    objective_values: dict[str, float] | None
    variable_values: dict[str, "VariableType"] | None


class SavedSolutionReference(SQLModel):
    saved_solution: UserSavedSolutionDB = Field(description="The reference object with the solution information.")

    @computed_field
    @property
    def name(self) -> str | None:
        return self.saved_solution.name

    @computed_field
    @property
    def objective_values(self) -> dict[str, float]:
        return self.saved_solution.objective_values

    @computed_field
    @property
    def variable_values(self) -> dict[str, VariableType]:
        return self.saved_solution.variable_values

    @computed_field
    @property
    def solution_index(self) -> int | None:
        return self.saved_solution.solution_index

    @computed_field
    @property
    def saved_solution_id(self) -> int:
        return self.saved_solution.id

    @computed_field
    @property
    def state_id(self) -> int | None:
        return self.saved_solution.origin_state_id


class SavedSolutionResponse(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None
    objective_values: dict[str, float]
    variable_values: dict[str, VariableType]


class UserSavedSolutionAddress(SolutionAddress):
    """Defines a schema for storing archived solutions."""

    name: str | None = Field(
        description="An optional name for the solution, useful for archiving purposes.",
        default=None,
    )

    def to_solution_address(self) -> SolutionAddress:
        """Convert UserSavedSolutionAddress to just SolutionAddress"""
        return SolutionAddress(
            objective_values=self.objective_values, address_state=self.address_state, address_result=self.address_result
        )
