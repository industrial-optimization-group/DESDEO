"""Models specific to the reference point method."""

from sqlmodel import JSON, Column, Field, SQLModel

from .preference import ReferencePoint


class RPMSolveRequest(SQLModel):
    """Model of the request to the reference point method."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    preference: ReferencePoint = Field(Column(JSON))
