"""Defines models for archiving solutions."""

from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from desdeo.tools.generics import SolverResults

if TYPE_CHECKING:
    from .problem import ProblemDB
    from .state import StateDB
    from .user import User
    from .session import InteractiveSessionDB


class UserSavedSolutionBase(SQLModel):
    """The base model of an archive entry."""

    variable_values: dict[str, float | list] = Field(
        sa_column=Column(JSON, nullable=False)
    )
    objective_values: dict[str, float] = Field(sa_column=Column(JSON, nullable=False))
    constraint_values: dict[str, float] | None = Field(
        sa_column=Column(JSON), default=None
    )
    extra_func_values: dict[str, float] | None = Field(
        sa_column=Column(JSON), default=None
    )


class UserSavedSolutionDB(UserSavedSolutionBase, table=True):
    """Database model of an archive entry."""

    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(
        default=None, nullable=True
    )  # Optional name for the solution
    user_id: int | None = Field(foreign_key="user.id", default=None)
    problem_id: int | None = Field(foreign_key="problemdb.id", default=None)
    state_id: int | None = Field(foreign_key="statedb.id", default=None)
    # Back populates
    user: "User" = Relationship(back_populates="archive")
    problem: "ProblemDB" = Relationship(back_populates="solutions")
    state: "StateDB" = Relationship(back_populates="saved_solutions")


class UserSavedSolverResults(SolverResults):
    """Defines a schema for storing archived solutions."""

    name: str | None = Field(
        description="An optional name for the solution, useful for archiving purposes.",
        default=None,
    )

    def to_solver_results(self) -> SolverResults:
        """Convert to SolverResults without the name field."""
        return SolverResults(
            optimal_variables=self.optimal_variables,
            optimal_objectives=self.optimal_objectives,
            constraint_values=self.constraint_values,
            extra_func_values=self.extra_func_values,
            scalarization_values=self.scalarization_values,
            success=self.success,
            message=self.message,
        )


class NonDominatedArchiveBase(SQLModel):
    """Base model for storing non-dominated archive data."""

    name: Optional[str] = Field(
        default=None, description="Optional name for the archive"
    )
    method: str = Field(description="EMO method used (e.g., 'nsga3', 'rvea')")
    problem_id: int = Field(description="ID of the problem")
    user_id: int = Field(description="ID of the user who created this archive")
    state_id: Optional[int] = Field(
        default=None, description="ID of the state that created this archive"
    )

    # Archive metadata
    total_solutions: int = Field(description="Total number of solutions in the archive")
    generation_created: int = Field(
        default=1, description="Generation when archive was created"
    )
    max_evaluations: int = Field(description="Maximum evaluations used")
    number_of_vectors: int = Field(description="Number of reference vectors used")

    # Archive data
    solutions: List[dict] = Field(
        sa_column=Column(JSON, nullable=False),
        description="Decision variable values for all non-dominated solutions",
    )
    objectives: List[dict] = Field(
        sa_column=Column(JSON, nullable=False),
        description="Objective values for all non-dominated solutions",
    )
    constraints: Optional[List[dict]] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Constraint values for all non-dominated solutions",
    )

    # Preference information
    preference_type: Optional[str] = Field(
        default=None, description="Type of preference used"
    )
    preference_data: Optional[dict] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Preference data used during optimization",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the archive was created"
    )


class NonDominatedArchiveDB(NonDominatedArchiveBase, table=True):
    """Database model for storing non-dominated archives - one per session."""

    __tablename__ = "nondominatedarchive"

    id: Optional[int] = Field(primary_key=True, default=None)

    # Foreign key relationships - use session_id as unique identifier
    user_id: int = Field(foreign_key="user.id")
    session_id: int = Field(
        foreign_key="interactivesessiondb.id", unique=True
    )  # One archive per session
    problem_id: int = Field(foreign_key="problemdb.id")
    state_id: Optional[int] = Field(foreign_key="statedb.id", default=None)

    # Relationships
    user: "User" = Relationship(back_populates="archives")
    session: "InteractiveSessionDB" = Relationship(back_populates="archive")
    problem: "ProblemDB" = Relationship(back_populates="archives")
    state: Optional["StateDB"] = Relationship(back_populates="archives")


class NonDominatedArchiveCreate(SQLModel):
    """Model for creating a new non-dominated archive."""

    name: Optional[str] = None
    method: str
    problem_id: int
    state_id: Optional[int] = None

    # Archive metadata
    total_solutions: int
    generation_created: int = 1
    max_evaluations: int
    number_of_vectors: int

    # Archive data
    solutions: List[dict]
    objectives: List[dict]
    constraints: Optional[List[dict]] = None

    # Preference information
    preference_type: Optional[str] = None
    preference_data: Optional[dict] = None


class NonDominatedArchiveResponse(NonDominatedArchiveBase):
    """Response model for non-dominated archive."""

    id: int
    created_at: datetime


class UserSavedEMOResults(SQLModel):
    """Defines a schema for storing archived EMO solutions."""

    name: str | None = Field(
        description="An optional name for the solution, useful for archiving purposes.",
        default=None,
    )

    # EMO-specific solution data
    variable_values: dict[str, float] = Field(
        sa_column=Column(JSON, nullable=False),
        description="Decision variable values",
    )
    objective_values: dict[str, float] = Field(
        sa_column=Column(JSON, nullable=False),
        description="Objective function values",
    )
    constraint_values: dict[str, float] | None = Field(
        sa_column=Column(JSON),
        default=None,
        description="Constraint values",
    )
    extra_func_values: dict[str, float] | None = Field(
        sa_column=Column(JSON),
        default=None,
        description="Extra function values",
    )

    # EMO-specific metadata
    method: str = Field(description="EMO method used (e.g., 'nsga3', 'rvea')")
    generation: int = Field(default=1, description="Generation when solution was found")
    rank: int | None = Field(default=None, description="Pareto rank of the solution")
    crowding_distance: float | None = Field(
        default=None, description="Crowding distance"
    )

    def to_emo_results(self) -> dict:
        """Convert to EMOResults-compatible format."""
        return {
            "solutions": [self.variable_values],
            "outputs": [self.objective_values],
            "method": self.method,
            "converged": True,
            "iteration_count": self.generation,
            "archive_size": 1,
        }


class UserSavedEMOSolutionDB(SQLModel, table=True):
    """Database model for storing saved EMO solutions."""

    __tablename__ = "user_saved_emo_solutions"

    id: int | None = Field(primary_key=True, default=None)
    name: str | None = Field(default=None, nullable=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")
    problem_id: int = Field(foreign_key="problemdb.id")
    state_id: int | None = Field(foreign_key="statedb.id", default=None)
    session_id: int | None = Field(foreign_key="interactivesessiondb.id", default=None)

    # Solution data
    variable_values: dict[str, float] = Field(sa_column=Column(JSON, nullable=False))
    objective_values: dict[str, float] = Field(sa_column=Column(JSON, nullable=False))
    constraint_values: dict[str, float] | None = Field(
        sa_column=Column(JSON), default=None
    )
    extra_func_values: dict[str, float] | None = Field(
        sa_column=Column(JSON), default=None
    )

    # EMO metadata
    method: str = Field(description="EMO method used")
    generation: int = Field(default=1, description="Generation when solution was found")
    rank: int | None = Field(default=None, description="Pareto rank")
    crowding_distance: float | None = Field(
        default=None, description="Crowding distance"
    )

    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(back_populates="saved_emo_solutions")
    problem: "ProblemDB" = Relationship(back_populates="saved_emo_solutions")
    state: "StateDB" = Relationship(back_populates="saved_emo_solutions")
    session: "InteractiveSessionDB" = Relationship(back_populates="saved_emo_solutions")


class UserSavedEMOSolutionCreate(SQLModel):
    """Model for creating a saved EMO solution."""

    name: str | None = None
    variable_values: dict[str, float]
    objective_values: dict[str, float]
    constraint_values: dict[str, float] | None = None
    extra_func_values: dict[str, float] | None = None
    method: str
    generation: int = 1
    rank: int | None = None
    crowding_distance: float | None = None


class UserSavedEMOSolutionResponse(SQLModel):
    """Response model for saved EMO solution."""

    id: int
    name: str | None
    variable_values: dict[str, float]
    objective_values: dict[str, float]
    constraint_values: dict[str, float] | None
    extra_func_values: dict[str, float] | None
    method: str
    generation: int
    rank: int | None
    crowding_distance: float | None
    created_at: datetime
    user_id: int
    problem_id: int
    state_id: int | None
    session_id: int | None
