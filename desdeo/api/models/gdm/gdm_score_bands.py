"""Models for GDM Score Bands.

Idea is that in the very first iteration, the filtered indices contains the clustering
information on the entire data. Since on each iteration, the clustering is different,
we need to include the indices over and over again. Of course with time the amount of
indices will get smaller and smaller, and eventually be only ~10 solutions.
"""

from sqlmodel import Field, SQLModel

from desdeo.api.models.gdm.gdm_base import BaseGroupInfoContainer
from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult


class GDMSCOREBandInformation(BaseGroupInfoContainer):
    """Class for containing info on which band was voted for."""
    method: str = "gdm-score-bands"
    user_votes: dict[int, int] = Field(
        description="Dictionary of votes."
    )
    user_confirms: list[int] = Field(
        description="List of users who want to move on."
    )
    voting_results: int | None = Field(
        "The band id that was voted for. Are there more than one?"
    )
    # Maybe store this as something smarter?
    active_indices: list[int] = Field(
        description="A list of active indices. They reduce as we choose a score band."
    )
    score_bands_config: SCOREBandsConfig = Field(
        description="The configuration that led to this classification."
    )
    score_bands_result: SCOREBandsResult = Field(
        description="The results of the score bands."
    )

class GDMScoreBandsInitializationRequest(SQLModel):
    """Request class for initialization of score bands."""
    group_id: int = Field(
        description="The group to be initialized."
    )

    score_bands_config: SCOREBandsConfig = Field(
        description="The configuration for the initial score banding."
    )

class GDMSCOREBandsResponse(SQLModel):
    """Response class for GDMSCOREBands, whether it is initialization or not."""

    group_id: int = Field(
        description="The group in question."
    )
    group_iter_id: int = Field(
        description="ID of the latest group iteration."
    )
    result: SCOREBandsResult = Field(
        description="The results of the score bands procedure."
    )
