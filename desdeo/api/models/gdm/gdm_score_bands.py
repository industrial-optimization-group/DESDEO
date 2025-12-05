"""Models for GDM Score Bands.

Idea is that in the very first iteration, the filtered indices contains the clustering
information on the entire data. Since on each iteration, the clustering is different,
we need to include the indices over and over again. Of course with time the amount of
indices will get smaller and smaller, and eventually be only ~10 solutions.
"""

from sqlmodel import JSON, Column, Field, SQLModel

from desdeo.api.models.gdm.gdm_base import BaseGroupInfoContainer
from desdeo.gdm.score_bands import SCOREBandsGDMConfig, SCOREBandsGDMResult
from desdeo.problem.schema import VariableType
from desdeo.tools.score_bands import SCOREBandsResult


class GDMSCOREBandInformation(BaseGroupInfoContainer):
    """Class for containing info on which band was voted for."""
    method: str = "gdm-score-bands"
    user_votes: dict[str, int] = Field(
        description="Dictionary of votes."
    )
    user_confirms: list[int] = Field(
        description="List of users who want to move on."
    )
    score_bands_config: SCOREBandsGDMConfig = Field(
        description="The configuration that led to this classification."
    )
    score_bands_result: SCOREBandsGDMResult = Field(
        description="The results of the score bands."
    )


class GDMSCOREBandFinalSelection(BaseGroupInfoContainer):
    """Class for containing the final 10 or less solutions, the final solution and the votes that led to it."""
    method: str = "gdm-score-bands-final"
    user_votes: dict[str, int] = Field(
        description="Dictionary of votes."
    )
    user_confirms: list[int] = Field(
        description="List of users who want to move on."
    )

    """The 10 or less solutions to choose from"""
    solution_variables: dict[str, list[VariableType]] = Field(sa_column=Column(JSON))
    solution_objectives: dict[str, list[float]] = Field(sa_column=Column(JSON))

    """The selected (or generated??) of those 10 or less."""
    winner_solution_variables: dict[str, VariableType] = Field(sa_column=Column(JSON))
    winner_solution_objectives: dict[str, float] = Field(sa_column=Column(JSON))


class GDMScoreBandsInitializationRequest(SQLModel):
    """Request class for initialization of score bands."""
    group_id: int = Field(
        description="The group to be initialized."
    )
    score_bands_config: SCOREBandsGDMConfig = Field(
        description="The configuration for the initial score banding."
    )

class GDMScoreBandsVoteRequest(SQLModel):
    """Request for voting for a band."""
    group_id: int = Field(
        description="ID of the group in question"
    )
    vote: int = Field(
        description="The vote. Vaalisalaisuus."
    )

class GDMSCOREBandsResponse(SQLModel):
    """Response class for GDMSCOREBands, whether it is initialization or not."""
    method = "gdm-score-bands"
    group_id: int = Field(
        description="The group in question."
    )
    group_iter_id: int = Field(
        description="ID of the latest group iteration."
    )
    result: SCOREBandsResult = Field(
        description="The results of the score bands procedure."
    )

class GDMSCOREBandsDecisionResponse(SQLModel):
    """Response class for gdm score bands that includes the last 10 or less solutions."""
    method = "gdm-score-bands-final"
    group_id: int = Field(
        description="The group in question."
    )
    group_iter_id: int = Field(
        description="ID of the latest group iteration."
    )
    result: GDMSCOREBandFinalSelection = Field(
        description="The container for the solutions and the winner solution."
    )
