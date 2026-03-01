"""Generic models for the DESDEO API."""

from pydantic import ConfigDict
from sqlmodel import JSON, Column, Field, SQLModel

from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult

from .generic_states import SolutionReferenceResponse


class SolutionInfo(SQLModel):
    """Used when we wish to reference a solution in some `StateDB` stored in the database."""

    state_id: int = Field(description="State of the desired solution.")
    solution_index: int = Field(description="Index of the desired solution.")
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
        sa_column=Column(JSON),
        description="The first solution used when computing intermediate solutions.",
    )
    reference_solution_2: SolutionReferenceResponse = Field(
        sa_column=Column(JSON),
        description="The second solution used when computing intermediate solutions.",
    )
    intermediate_solutions: list[SolutionReferenceResponse] = Field(
        sa_column=Column(JSON), description="The intermediate solutions computed."
    )


class ScoreBandsRequest(SQLModel):
    """Model of the request to calculate SCORE bands parameters."""

    data: list[list[float]] = Field(description="Matrix of objective values")
    objs: list[str] = Field(description="Array of objective names for each column")

    # Optional parameters with defaults matching the score_bands.py functions
    dist_parameter: float = Field(default=0.05, description="Distance parameter for axis positioning")
    use_absolute_corr: bool = Field(default=False, description="Use absolute correlation values")
    distance_formula: int = Field(default=1, description="Distance formula (1 or 2)")
    flip_axes: bool = Field(default=True, description="Whether to flip axes based on correlation signs")
    clustering_algorithm: str = Field(default="DBSCAN", description="Clustering algorithm (DBSCAN or GMM)")
    clustering_score: str = Field(default="silhoutte", description="Clustering score metric")


class ScoreBandsResponse(SQLModel):
    """Model of the response containing SCORE bands parameters."""

    groups: list[int] = Field(description="Cluster group assignments for each data point")
    axis_dist: list[float] = Field(description="Normalized axis positions")
    axis_signs: list[int] | None = Field(description="Axis direction signs (1 or -1)")
    obj_order: list[int] = Field(description="Optimal order of objectives")


class GroupScoreRequest(SQLModel):
    """A generic model for requesting SCORE Bands for a state."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    problem_id: int
    group_id: int
    """Database ID of the problem to solve."""
    session_id: int | None = Field(default=None)
    parent_state_id: int | None = Field(default=None)
    """State ID of the parent state, if any."""

    config: SCOREBandsConfig | None = Field(default=None)
    """Configuration for the SCORE bands visualization."""

    solution_ids: list[int] = Field()
    """List of solution IDs to score."""


class GroupScoreResponse(SQLModel):
    """Model of the response to an EMO score request."""

    model_config = ConfigDict(use_attribute_docstrings=True)

    group_iteration_id: int | None = Field(default=None)
    """The state ID of the newly created group iteration."""

    result: SCOREBandsResult
