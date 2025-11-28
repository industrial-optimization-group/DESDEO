"""Models for GDM Score Bands.

Idea is that in the very first iteration, the filtered indices contains the clustering
information on the entire data. Since on each iteration, the clustering is different,
we need to include the indices over and over again. Of course with time the amount of
indices will get smaller and smaller, and eventually be only ~10 solutions.
"""

from sqlmodel import Field

from desdeo.api.models import BaseGroupInfoContainer
from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult


class GDMSCOREBandInformation(BaseGroupInfoContainer):
    """Class for containing info on which band was voted for."""
    user_votes: dict[int, int] = Field(
        description="Dictionary of votes."
    )
    user_confirms: dict[int, bool] = Field(
        description="Info on whether every user wants to move on."
    )
    voting_results: int | None = Field(
        "The band id that was voted for. Are there more than one?"
    )
    # Maybe store this as something smarter?
    filtered_indices: list[(int, int)] = Field(
        description="A list of tuples where 1st is the discrete index and 2nd is its cluster."
    )
