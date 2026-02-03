"""Requests models."""
from pydantic import BaseModel


class RepresentativeSolutionSetRequest(BaseModel):
    """Model of the request to the representative solution set."""
    problem_id: int
    name: str
    description: str | None = None
    solution_data: dict[str, list[float]]
    ideal: dict[str, float]
    nadir: dict[str, float]
