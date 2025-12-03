"""Necessary routers for GDM Score Bands.

I imagine these as simple interfaces to the GDMScoreBandsManager.
"""
from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    GDMSCOREBandInformation,
    GDMScoreBandsInitializationRequest,
    GDMSCOREBandsResponse,
    Group,
    GroupIteration,
    User,
    GroupInfoRequest,
)
from desdeo.api.routers.gdm.gdm_aggregate import manager
from desdeo.api.routers.gdm.gdm_score_bands.gdm_score_bands_manager import GDMScoreBandsManager
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult, score_json

router = APIRouter(prefix="/gdm-score-bands", tags=["GDM Score Bands"])

@router.post("/vote")
async def vote_for_a_band(
    group_id: int,
    vote: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Vote for a band.

    Args:
        group_id (int): _description_
        vote (int): _description_
        user (Annotated[User, Depends): _description_
        session (Annotated[Session, Depends): _description_
    """
    group = session.exec(select(Group).where(Group.id == group_id)).first()
    if not group:
        raise HTTPException(
            detail=f"Group with ID {group_id} does not exist!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    if user.id not in group.user_ids:
        raise HTTPException(
            detail=f"User with ID {user.id} is not part of group with ID {group.id}. Could be the owner though.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    try:
        group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
            group_id=group_id, method="gdm-score-bands"
        )
    except Exception as e:
        print(e)

    # This would be the better way to do things.
    try:
        await group_mgr.vote(
            user=user,
            group=group,
            voted_index=vote,
            session=session
        )
    except Exception as e:
        raise HTTPException(
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e

    return JSONResponse(
        content={"message": f"Voted for index {vote} by user with ID {user.id}"}
    )

@router.post("/confirm")
async def confirm_vote(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Confirm that you'll want to use these preferences.

    Args:
        group_id (int): _description_
        vote (int): _description_
        user (Annotated[User, Depends): _description_
        session (Annotated[Session, Depends): _description_
    """
    group = session.exec(select(Group).where(Group.id == group_id)).first()
    if not group:
        raise HTTPException(
            detail=f"Group with ID {group_id} does not exist!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    if user.id not in group.user_ids:
        raise HTTPException(
            detail=f"User with ID {user.id} is not part of group with ID {group.id}. Could be the owner though.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_id=group_id, method="gdm-score-bands"
    )
    try:
        await group_mgr.confirm(
            user=user,
            group=group,
            session=session
        )
    except Exception as e:
        raise HTTPException(
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e

    return JSONResponse(
        content={"message": f"Confirmed vote and moving on for user with ID {user.id}"}
    )

@router.post("/get-or-initialize")
async def initialize(
    request: GDMScoreBandsInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> GDMSCOREBandsResponse:
    """Initialize the GDM SCORE BANDS."""
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if not Group:
        raise HTTPException(
            detail=f"Group with ID {request.group_id} not found!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    if group.head_iteration_id is not None:
        # Actually, just return the newest score band data,.
        print("Group already initialized!")
        group_iteration = session.exec(
            select(GroupIteration).where(GroupIteration.id == group.head_iteration_id)
        ).first()
        return GDMSCOREBandsResponse(
            group_id=group.id,
            group_iter_id=group.head_iteration_id,
            result=group_iteration.info_container.score_bands_result
        )
    user_ids = group.user_ids
    user_ids.append(group.owner_id)
    if user.id not in user_ids:
        raise HTTPException(
            detail=f"User with ID {user.id} is not part of group with ID {group.id}",
            status_code=status.HTTP_403_FORBIDDEN
        )
    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_id=group.id, method="gdm-score-bands"
    )

    score_bands_config = SCOREBandsConfig() if request.score_bands_config is None else request.score_bands_config

    # initial clustering for the objectives
    discrete_representation_obj = group_mgr.discrete_representation.objective_values
    objs = pl.DataFrame(discrete_representation_obj)
    result: SCOREBandsResult = score_json(
        data=objs,
        options=score_bands_config
    )

    # all solutions are active.
    active_indices = list(range(len(result.clusters)))

    # store necessary data to the database. Currently all "voting" related is null bc no voting has happened yet.
    score_bands_info = GDMSCOREBandInformation(
        user_votes={},
        user_confirms=[],
        voting_results=None,
        active_indices=active_indices,
        score_bands_config=score_bands_config,
        score_bands_result=result
    )

    # Add group iteration and related stuff, then set new iteration to head.
    iteration: GroupIteration = GroupIteration(
        group_id=group.id,
        problem_id=group.problem_id,
        info_container=score_bands_info,
        notified={},
        state_id=None,
        parent_id=None,
        parent=None,
    )

    session.add(iteration)
    session.commit()
    session.refresh(iteration)

    group.head_iteration_id = iteration.id
    session.add(group)
    session.commit()
    session.refresh(group)

    # Actually, return just the newly created score band data.
    return GDMSCOREBandsResponse(
        group_id=group.id,
        group_iter_id=group.head_iteration_id,
        result=result
    )

@router.post("/get-votes-and-confirms")
def get_votes_and_confirms(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> JSONResponse:
    """Returns the current status of votes and confirmations in this iteration.

    Args:
        request (GroupInfoRequest): The group we'd like the info on.
        user (Annotated[User, Depends): The user that requests the data.
        session (Annotated[Session, Depends): The database session.

    Raises:
        HTTPException: If group doesn't exists etc errors.

    Returns:
        JSONResponse: A response containing the votes and confirmations.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if not Group:
        raise HTTPException(
            detail=f"Group with ID {request.group_id} not found!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    if group.head_iteration_id is None:
        raise HTTPException(
            detail="Group hasn't been initialized!",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    user_ids = group.user_ids
    user_ids.append(group.owner_id)
    if user.id not in user_ids:
        raise HTTPException(
            detail="Unauthorized user!",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    iteration = session.exec(select(GroupIteration).where(GroupIteration.id == group.head_iteration_id)).first()
    votes = iteration.info_container.user_votes
    confirms = iteration.info_container.user_confirms

    return JSONResponse(
        content={
            "votes": votes,
            "confirms": confirms
        }
    )
