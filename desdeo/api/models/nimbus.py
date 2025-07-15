"""Models specific to the nimbus method."""

from sqlmodel import JSON, Column, Field, SQLModel

from desdeo.api.models.archive import UserSavedSolverResults

from .preference import ReferencePoint


class NIMBUSClassificationRequest(SQLModel):
    """Model of the request to the nimbus method."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    preference: ReferencePoint = Field(Column(JSON))

    current_objectives: dict[str, float] = Field(sa_column=Column(JSON))
    num_desired: int | None = Field(default=1)

class NIMBUSSaveRequest(SQLModel):
    """Request model for saving solutions from any method's state."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    solutions: list[UserSavedSolverResults]  # List of solutions to save
class NIMBUSInitializationRequest(SQLModel):
    """Model of the request to the nimbus method."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    solver: str | None = Field(default=None)
