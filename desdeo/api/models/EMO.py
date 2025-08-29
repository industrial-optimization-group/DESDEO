"""Models specific to the evolutionary multiobjective optimization (EMO) methods."""

from typing import Dict, List, Optional, Union

from sqlmodel import JSON, Column, Field, SQLModel

from desdeo.api.models.archive import UserSavedEMOResults
from desdeo.api.models.preference import (
    NonPreferredSolutions,
    PreferredRanges,
    PreferredSolutions,
    ReferencePoint,
)
from desdeo.api.models.session import InteractiveSessionDB
from desdeo.api.models.state import StateDB


class EMOSolveRequest(SQLModel):
    """Request model for starting EMO optimization."""

    problem_id: int
    method: str = Field(default="NSGA3", description="EMO method: 'NSGA3' or 'RVEA'")
    max_evaluations: int = Field(default=50000, description="Maximum number of function evaluations")
    number_of_vectors: int = Field(default=30, description="Number of reference vectors")
    use_archive: bool = Field(default=True, description="Whether to use solution archive")

    # Use Union to accept different preference types
    preference: Union[ReferencePoint, PreferredSolutions, NonPreferredSolutions, PreferredRanges] = Field(
        description="Preference information for interactive adaptation"
    )
    session_id: Optional[int] = Field(default=None, description="Interactive session ID")
    parent_state_id: Optional[int] = Field(default=None, description="Parent state ID for continuation")


class EMOSaveRequest(SQLModel):
    """Request model for saving selected EMO solutions."""

    problem_id: int
    session_id: Optional[int] = None
    parent_state_id: Optional[int] = None

    # List of solutions to save
    solutions: List[UserSavedEMOResults] = Field(description="List of EMO solutions to save with optional names")
