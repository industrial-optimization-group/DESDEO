"""Necessary routers for GDM Score Bands.

I imagine these as simple interfaces to the GDMScoreBandsManager.
"""
import logging
import sys
from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    GDMSCOREBandInformation,
    GDMSCOREBandsDecisionResponse,
    GDMScoreBandsInitializationRequest,
    GDMSCOREBandsResponse,
    GDMSCOREBandsRevertRequest,
    GDMScoreBandsVoteRequest,
    Group,
    GroupInfoRequest,
    GroupIteration,
    User,
)
from desdeo.api.routers.gdm.gdm_aggregate import manager
from desdeo.api.routers.gdm.gdm_score_bands.gdm_score_bands_manager import GDMScoreBandsManager
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.gdm.score_bands import SCOREBandsGDMConfig, SCOREBandsGDMResult, score_bands_gdm

logging.basicConfig(
    stream=sys.stdout, format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdm-score-bands", tags=["GDM Score Bands"])

@router.post("/vote")
async def vote_for_a_band(
    request: GDMScoreBandsVoteRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
):
    """Vote for a band using this endpoint.

    Args:
        request (GDMScoreBandsVoteRequest): A container for the group id and the vote.
        user (Annotated[User, Depends): the current user.
        session (Annotated[Session, Depends): database session

    Raises:
        HTTPException: If something goes wrong. It hopefully let's you know what went wrong.

    Returns:
        JSONResponse: A quick confirmation that vote went through.
    """
    group_id = request.group_id
    vote = request.vote
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
        logger.exception(e)
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e

    return JSONResponse(
        content={"message": f"Voted for index {vote} by user with ID {user.id}"}
    )

@router.post("/confirm")
async def confirm_vote(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Confim the vote. If all confirm, the clustering and new iteration begins.

    Args:
        request (GroupInfoRequest): Simple request to get the group ID.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): Database session.

    Raises:
        HTTPException: If something goes awry. It should let you know what went wrong, though.

    Returns:
        JSONResponse: A simple confirmation that everything went ok and that vote went in.
    """
    group_id = request.group_id
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
        logger.exception(e)
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e

    return JSONResponse(
        content={"message": f"Confirmed vote and moving on for user with ID {user.id}"}
    )

@router.post("/get-or-initialize")
async def get_or_initialize(
    request: GDMScoreBandsInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> GDMSCOREBandsResponse | GDMSCOREBandsDecisionResponse:
    """An endpoint for two things: Initializing the GDM Score Bands things and Fetching results.

    If a group hasn't been initialized, initialize and then return initial clustering information.
    If it has been initialized, just fetch the latest iteration's information (clustering, etc.)

    Args:
        request (GDMScoreBandsInitializationRequest): Request that contains necessary information for initialization.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): Database session.

    Raises:
        HTTPException: It'll let you know.

    Returns:
        GDMSCOREBandsResponse: A response containing Group id, group iter id and ScoreBandsResponse.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if not group:
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
        match group_iteration.info_container.method:
            case "gdm-score-bands":
                return GDMSCOREBandsResponse(
                    group_id=group.id,
                    group_iter_id=group.head_iteration_id,
                    latest_iteration=group_iteration.info_container.score_bands_result.iteration,
                    result=group_iteration.info_container.score_bands_result.score_bands_result
                )
            case "gdm-score-bands-final":
                return GDMSCOREBandsDecisionResponse(
                    group_id=group.id,
                    group_iter_id=group.head_iteration_id,
                    result=group_iteration.info_container
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

    score_bands_config = SCOREBandsGDMConfig() if request.score_bands_config is None else request.score_bands_config

    # initial clustering for the objectives
    discrete_representation_obj = group_mgr.discrete_representation.objective_values
    objs = pl.DataFrame(discrete_representation_obj)
    result: SCOREBandsGDMResult = score_bands_gdm(
        data=objs,
        config=score_bands_config,
        state=None
    )[-1]

    # store necessary data to the database. Currently all "voting" related is null bc no voting has happened yet.
    score_bands_info = GDMSCOREBandInformation(
        user_votes={},
        user_confirms=[],
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
        latest_iteration=result.iteration,
        result=result.score_bands_result
    )

@router.post("/get-votes-and-confirms")
def get_votes_and_confirms(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> JSONResponse:
    """Returns the current status of votes and confirmations in current iteration.

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


@router.post("/revert")
async def revert(
    request: GDMSCOREBandsRevertRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Revert to a previous iteration. Usable only by the analyst.

    This implies that we're gonna need to see ALL previous iterations I'd say.

    Args:
        request (GDMSCOREBandsRevertRequest): The request containing group id and iteration number.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): The database session.

    Returns:
        JSONResponse: Acknowledgement of the revert.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if user.id is not group.owner_id:
        raise HTTPException(
            detail="Reverting can only be done by the group owner!",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    if not group:
        raise HTTPException(
            detail=f"Group with ID {request.group_id} not found!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    user_ids = group.user_ids
    user_ids.append(group.owner_id)
    if user.id not in user_ids:
        raise HTTPException(
            detail=f"User with ID {user.id} is not part of group with ID {group.id}",
            status_code=status.HTTP_403_FORBIDDEN
        )
    group_id = request.group_id
    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_id=group_id, method="gdm-score-bands"
    )

    try:
        await group_mgr.revert(
            user=user,
            group=group,
            session=session,
            group_iteration_number=request.iteration_number
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e

    return JSONResponse(
        content={"message": "Reverted iteration."}
    )

@router.post("/configure")
async def configure_gdm(
    config: SCOREBandsGDMConfig,
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> JSONResponse:
    """Configure the SCORE Bands settings.

    Args:
        config (SCOREBandsGDMConfig): The configuration object
        group_id (int): group id
        user (Annotated[User, Depends): The user doing the request
        session (Annotated[Session, Depends): The database session.

    Returns:
        JSONResponse: Acknowledgement that yeah ok reconfigured.
    """
    group: Group = session.exec(select(Group).where(Group.id == group_id)).first()
    if user.id is not group.owner_id:
        raise HTTPException(
            detail="Reverting can only be done by the group owner!",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    if not group:
        raise HTTPException(
            detail=f"Group with ID {group_id} not found!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    user_ids = group.user_ids
    user_ids.append(group.owner_id)
    if user.id not in user_ids:
        raise HTTPException(
            detail=f"User with ID {user.id} is not part of group with ID {group.id}",
            status_code=status.HTTP_403_FORBIDDEN
        )
    group_mgr: GDMScoreBandsManager = await manager.get_group_manager(
        group_id=group_id, method="gdm-score-bands"
    )

    try:
        await group_mgr.configure(
            config=config,
            group=group,
            session=session,
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            detail=f"Internal server error: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e

    return JSONResponse(
        content={"message": "Configured. Re-clustered."}
    )
