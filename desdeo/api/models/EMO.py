"""Models specific to the evolutionary multiobjective optimization (EMO) methods."""

from typing import Dict, List, Optional, ClassVar, Union
from sqlmodel import SQLModel, Field, Column, JSON
from desdeo.api.models.preference import (
    PreferenceBase,
    ReferencePoint,
    PreferedSolutions,
    NonPreferredSolutions,
    PreferredRanges,
)
from desdeo.api.models.session import InteractiveSessionDB
from desdeo.api.models.state import StateDB


class EMOSolveRequest(SQLModel):
    """Request model for starting EMO optimization."""

    problem_id: int
    method: str = Field(default="nsga3", description="EMO method: 'nsga3' or 'rvea'")
    max_evaluations: int = Field(
        default=50000, description="Maximum number of function evaluations"
    )
    number_of_vectors: int = Field(
        default=30, description="Number of reference vectors"
    )
    use_archive: bool = Field(
        default=True, description="Whether to use solution archive"
    )

    # Use Union to accept different preference types
    preference: Union[
        ReferencePoint, PreferedSolutions, NonPreferredSolutions, PreferredRanges
    ] = Field(description="Preference information for interactive adaptation")
    session_id: Optional[int] = Field(
        default=None, description="Interactive session ID"
    )
    parent_state_id: Optional[int] = Field(
        default=None, description="Parent state ID for continuation"
    )


class EMOResults(SQLModel):
    """Model for storing EMO optimization results."""

    solutions: List[Dict[str, float]] = Field(
        sa_column=Column(JSON), description="Decision variable values"
    )
    outputs: List[Dict[str, float]] = Field(
        sa_column=Column(JSON), description="Objective function values"
    )
    archive_solutions: Optional[List[Dict[str, float]]] = Field(
        sa_column=Column(JSON),
        default=None,
        description="Archive of non-dominated solutions",
    )
    method: str = Field(description="EMO method used")
    converged: bool = Field(default=False, description="Whether optimization converged")
    iteration_count: int = Field(
        default=1, description="Number of iterations performed"
    )
    archive_size: Optional[int] = Field(
        default=None, description="Size of solution archive"
    )


class EMOState(SQLModel):
    """Model for EMO optimization state."""

    method: str = Field(description="EMO method being used")
    max_evaluations: int = Field(description="Maximum number of function evaluations")
    number_of_vectors: int = Field(description="Number of reference vectors")
    use_archive: bool = Field(description="Whether solution archive is being used")
    results: EMOResults = Field(
        sa_column=Column(JSON), description="Optimization results"
    )
