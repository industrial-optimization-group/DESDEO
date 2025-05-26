"""Generic models for the DESDEO API."""

from sqlmodel import JSON, Column, Field, SQLModel

class IntermediateSolutionRequest(SQLModel):
    """Model of the request to solve intermediate solutions between two solutions."""
    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)

    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    num_desired: int | None = Field(default=1)

    reference_solution_1: dict[str, float]
    reference_solution_2: dict[str, float]
