"""GNIMBUS specific data classes"""

from sqlmodel import Field, Column

from desdeo.api.models import (
    BasePreferenceResults, 
    ReferencePointDictType, 
    ReferencePoint,
    SolverResultType,
)
from desdeo.tools import SolverResults


class GNIMBUSPreferenceResults(BasePreferenceResults):
    """A GNIMBUS preference and result class"""
    method: str = "gnimbus"
    set_preferences: dict[int, ReferencePoint] = Field(sa_column=Column(ReferencePointDictType))
    results: list[SolverResults] = Field(sa_column=Column(SolverResultType))


class VotingPreferenceResults(BasePreferenceResults):
    """A voting preferences and results. A placeholder, really"""
    method: str = "voting"
    set_preferences: dict[int, int] = Field() # A user votes for an index from the results (or something)
    results: SolverResults = Field() # The winning result (or something)