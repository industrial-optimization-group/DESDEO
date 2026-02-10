from sqlmodel import SQLModel  # noqa: D100


class RepresentativeSolutionSetBase(SQLModel):
    """Shared base model for representative solution sets."""

    name: str
    description: str | None = None
    solution_data: dict[str, list[float]]
    ideal: dict[str, float]
    nadir: dict[str, float]

class RepresentativeSolutionSetRequest(RepresentativeSolutionSetBase):
    """Model of the request to the representative solution set."""

    problem_id: int

class RepresentativeSolutionSetInfo(SQLModel):
    """Model of the representative solution set info."""

    id: int
    problem_id: int
    name: str
    description: str | None = None
    ideal: dict[str, float]
    nadir: dict[str, float]

class RepresentativeSolutionSetFull(
    RepresentativeSolutionSetInfo
):
    """Model of the representative solution set full info."""
    solution_data: dict[str, list[float]]
