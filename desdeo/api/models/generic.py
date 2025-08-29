"""Generic models for the DESDEO API."""

from sqlmodel import JSON, Column, Field, SQLModel

from .generic_states import SolutionReferenceResponse


class SolutionInfo(SQLModel):
    """Used when we wish to reference a solution in some `StateDB` stored in the database."""

    state_id: int
    solution_index: int
    name: str | None = Field(description="Name to be given to the solution. Optional.", default=None)


class IntermediateSolutionRequest(SQLModel):
    """Model of the request to solve intermediate solutions between two solutions."""

    problem_id: int
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    context: str | None = None  # Method context (nimbus, rpm, etc.)
    scalarization_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)
    solver: str | None = Field(default=None)
    solver_options: dict[str, float | str | bool] | None = Field(sa_column=Column(JSON), default=None)

    num_desired: int | None = Field(default=1)

    reference_solution_1: SolutionInfo
    reference_solution_2: SolutionInfo


class GenericIntermediateSolutionResponse(SQLModel):
    """The response from computing intermediate values."""

    state_id: int | None = Field(description="The newly created state id")
    reference_solution_1: SolutionReferenceResponse = Field(
        sa_column=Column(JSON), description="The first solution used when computing intermediate solutions."
    )
    reference_solution_2: SolutionReferenceResponse = Field(
        sa_column=Column(JSON), description="The second solution used when computing intermediate solutions."
    )
    intermediate_solutions: list[SolutionReferenceResponse] = Field(
        sa_column=Column(JSON), description="The intermediate solutions computed."
    )
