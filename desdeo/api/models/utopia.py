"""Request and response models for Utopia endpoint"""

from typing import Any
from sqlmodel import SQLModel, Field
from .state_table import SolutionAddress


class UtopiaRequest(SQLModel):
    """The request for an Utopia map."""

    problem_id: int = Field(description="Problem for which the map is generated")
    solution: SolutionAddress = Field(description="Solution for which to generate the map")


class UtopiaResponse(SQLModel):
    """The response to an UtopiaRequest."""

    is_utopia: bool = Field(description="True if map exists for this problem.")
    map_name: str = Field(description="Name of the map.")
    map_json: dict[str, Any] = Field(description="MapJSON representation of the geography.")
    options: dict[str, Any] = Field(description="A dict with given years as keys containing options for each year.")
    description: str = Field(description="Description shown above the map.")
    years: list[str] = Field(description="A list of years for which the maps have been generated.")
