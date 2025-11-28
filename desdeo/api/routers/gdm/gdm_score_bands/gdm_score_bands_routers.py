"""Necessary routers for GDM Score Bands.

I imagine these as simple interfaces to the GDMScoreBandsManager.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from desdeo.api.db import get_session
from desdeo.api.models import Group, User
from desdeo.api.routers.gdm.gdm_aggregate import manager
from desdeo.api.routers.gdm.gdm_score_bands.gdm_score_bands_manager import GDMScoreBandsManager
from desdeo.api.routers.user_authentication import get_current_user

router = APIRouter(prefix="/gdm-score-bands", tags=["GDM Score Bands"])

@router.post("/vote")
async def vote_for_a_band(
    group_id: int,
    vote: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Yea.

    Args:
        group_id (int): _description_
        vote (int): _description_
        user (Annotated[User, Depends): _description_
        session (Annotated[Session, Depends): _description_
    """
    try:
        group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
            group_id=group_id, method="gdm-score-bands"
        )
    except Exception as e:
        print(e)

    # This would be the better way to do things.
    await group_mgr.vote(
        user_id=user.id,
        group_id=group_id,
        voted_index=vote,
        session=session
    )

@router.post("/confirm")
async def confirm_vote(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Oh yeah.

    Args:
        group_id (int): _description_
        vote (int): _description_
        user (Annotated[User, Depends): _description_
        session (Annotated[Session, Depends): _description_
    """
    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_id=group_id, method="gdm-score-bands"
    )
    await group_mgr.confirm(
        user_id=user.id,
        group_id=group_id,
        session=session
    )

@router.post("/initialize")
async def initialize(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Initialize the GDM SCORE BANDS."""
    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_id=group_id, method="gdm-score-bands"
    )
    print(type(group_mgr))
