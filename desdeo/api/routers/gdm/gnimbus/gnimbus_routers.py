"""GNIMBUS routers.

Separated from GNIMBUSManager file for
A.) Clarity and
B.) To avoid circular imports, since we need to access the ManagerManager singleton.
"""

import copy
import logging
import sys
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    FullIteration,
    GNIMBUSAllIterationsResponse,
    GNIMBUSResultResponse,
    GNIMBUSSwitchPhaseRequest,
    GNIMBUSSwitchPhaseResponse,
    GNIMBUSVotingState,
    Group,
    GroupInfoRequest,
    GroupIteration,
    OptimizationPreference,
    ProblemDB,
    SolutionReference,
    StateDB,
    User,
    VotingPreference,
)
from desdeo.api.routers.gdm.gdm_aggregate import manager
from desdeo.api.routers.problem import check_solver
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.nimbus import generate_starting_point
from desdeo.problem import Problem

logging.basicConfig(
    stream=sys.stdout, format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)

not_init_error = HTTPException(detail="Problem has not been initialized!", status_code=status.HTTP_400_BAD_REQUEST)

router = APIRouter(prefix="/gnimbus")


@router.post("/initialize")
def gnimbus_initialize(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Initialize the problem for GNIMBUS."""
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found!", status_code=status.HTTP_404_NOT_FOUND)
    if not (user.id in group.user_ids or user.id is group.owner_id):
        raise HTTPException(detail="Unauthorized user", status_code=status.HTTP_401_UNAUTHORIZED)

    if group.head_iteration is not None:
        raise HTTPException(detail="Group problem already initialized!", status_code=status.HTTP_400_BAD_REQUEST)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
    if problem_db is None:
        raise HTTPException(
            detail=f"No problem with id {group.problem_id} found!", status_code=status.HTTP_404_NOT_FOUND
        )

    solver = check_solver(problem_db=problem_db)

    problem = Problem.from_problemdb(problem_db)

    # Create the first iteration for the group
    # As if we just voted for a result, but really is just the starting point.
    starting_point = generate_starting_point(problem=problem, solver=solver)

    gnimbus_state = GNIMBUSVotingState(votes={}, solver_results=[starting_point])

    state = StateDB.create(
        database_session=session, problem_id=problem_db.id, session_id=None, parent_id=None, state=gnimbus_state
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    start_iteration = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        group=group,
        preferences=VotingPreference(
            set_preferences={},
        ),
        notified={},
        state_id=state.id,
        parent_id=None,
        parent=None,
        child=None,
    )

    session.add(start_iteration)
    session.commit()
    session.refresh(start_iteration)

    new_iteration = GroupIteration(
        problem_id=start_iteration.problem_id,
        group_id=start_iteration.group_id,
        group=start_iteration.group,
        preferences=OptimizationPreference(
            set_preferences={},
        ),
        notified={},
        parent_id=start_iteration.id,
        parent=start_iteration,
        child=None,
    )

    session.add(new_iteration)
    session.commit()
    session.refresh(new_iteration)

    start_iteration.child = new_iteration
    session.add(start_iteration)
    group.head_iteration = new_iteration
    session.add(group)
    session.commit()

    return JSONResponse(content={"message": f"Group {group.id} initialized."}, status_code=status.HTTP_200_OK)


@router.post("/get_latest_results")
def get_latest_results(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GNIMBUSResultResponse:
    """Get the latest results from group iteration.

    Args:
        request (GroupInfoRequest): essentially just the ID of the group
        user (Annotated[User, Depends(get_current_user)]): Current user
        session (Annotated[Session, Depends(get_session)]): Database session.

    Returns:
        GNIMBUSResultResponse: A GNIMBUSResultResponse response containing the latest gnimbus results

    Raises:
        HTTPException: Validation errors or no results
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found", status_code=status.HTTP_404_NOT_FOUND)

    if not (user.id in group.user_ids or user.id is group.owner_id):
        raise HTTPException(detail="Unauthorized user.", status_code=status.HTTP_401_UNAUTHORIZED)

    nores_exp = HTTPException(detail="No results found!", status_code=status.HTTP_404_NOT_FOUND)

    try:
        iteration = group.head_iteration.parent
    except Exception as e:
        raise nores_exp from e

    if iteration is None:
        raise nores_exp

    state = session.exec(select(StateDB).where(StateDB.id == iteration.state_id)).first()
    if state is None:
        raise nores_exp

    actual_state = state.state
    preferences = iteration.preferences

    if type(actual_state) is GNIMBUSVotingState:
        return GNIMBUSResultResponse(
            method="voting",
            phase=iteration.parent.preferences.phase if iteration.parent is not None else "learning",
            preferences=preferences,
            common_results=[SolutionReference(state=state, solution_index=0)],
            user_results=[],
            personal_result_index=None,
        )

    personal_result_index = None
    for i, item in enumerate(preferences.set_preferences.items()):
        if item[0] == user.id:
            personal_result_index = i
            break

    if personal_result_index is None:
        raise HTTPException(detail=f"No personal results for user ID {user.id}", status_code=status.HTTP_404_NOT_FOUND)

    solution_references = []
    for i, _ in enumerate(actual_state.solver_results):
        solution_references.append(SolutionReference(state=state, solution_index=i))

    return GNIMBUSResultResponse(
        method="optimization",
        phase=iteration.preferences.phase,
        preferences=preferences,
        common_results=solution_references[-4:],
        user_results=solution_references[:-4],
        personal_result_index=personal_result_index,
    )


@router.post("/all_iterations")
def full_iteration(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GNIMBUSAllIterationsResponse:
    """Get all results from all iterations of the group.

    Args:
        request (GroupInfoRequest): essentially just the ID of the group
        user (Annotated[User, Depends(get_current_user)]): current user
        session (Annotated[Session, Depends(get_session)]): current session

    Returns:
        GNIMBUSAllIterationsResponse: A GNIMBUSAllIterationsResponse response
        containing all the results of the iterations. If last iteration was optimization,
        the first iteration is incomplete (i.e. the voting preferences and voting results are missing)

    Raises:
        HTTPException: Validation errors or no results or no states and such.
    """
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id}!", status_code=status.HTTP_404_NOT_FOUND)

    if user.id not in group.user_ids and user.id is not group.owner_id:
        raise HTTPException(detail="Unauthorized user", status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        groupiter = group.head_iteration.parent
    except Exception as e:
        raise not_init_error from e

    if groupiter is None:
        raise not_init_error

    full_iterations: list[FullIteration] = []

    if groupiter.preferences.method == "optimization":
        # There are no full results because the latest iteration is optimization,
        # so add an incomplete entry to the list to be returned.
        prev_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.state_id)).first()
        if prev_state is None:
            raise HTTPException(detail="No state for starting results!", status_code=status.HTTP_404_NOT_FOUND)

        this_state = session.exec(select(StateDB).where(StateDB.id == groupiter.state_id)).first()
        if this_state is None:
            raise HTTPException(detail="No state in most recent iteration!", status_code=status.HTTP_404_NOT_FOUND)

        personal_result_index = None
        for i, item in enumerate(groupiter.preferences.set_preferences.items()):
            if item[0] == user.id:
                personal_result_index = i
                break

        all_results = []
        for i, _ in enumerate(this_state.state.solver_results):
            all_results.append(SolutionReference(state=this_state, solution_index=i))

        full_iterations.append(
            FullIteration(
                phase=groupiter.preferences.phase,
                optimization_preferences=groupiter.preferences,
                voting_preferences=None,
                starting_result=SolutionReference(state=prev_state, solution_index=0),
                common_results=all_results[-4:],
                user_results=all_results[:-4],
                personal_result_index=personal_result_index,
                final_result=None,
            )
        )

        groupiter = groupiter.parent

    # We're at voting/end method now.
    while groupiter is not None and groupiter.parent is not None and groupiter.parent.parent is not None:
        this_state = session.exec(select(StateDB).where(StateDB.id == groupiter.state_id)).first()
        prev_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.state_id)).first()
        first_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.parent.state_id)).first()

        if this_state is None or prev_state is None or first_state is None:
            raise HTTPException(detail="All needed states do not exist!", status_code=status.HTTP_404_NOT_FOUND)

        all_results = []
        for i, _ in enumerate(prev_state.state.solver_results):
            all_results.append(SolutionReference(state=prev_state, solution_index=i))

        personal_result_index = None
        for i, item in enumerate(groupiter.parent.preferences.set_preferences.items()):
            if item[0] == user.id:
                personal_result_index = i
                break

        full_iterations.append(
            FullIteration(
                phase=groupiter.parent.preferences.phase,
                optimization_preferences=groupiter.parent.preferences,
                voting_preferences=groupiter.preferences,
                starting_result=SolutionReference(state=first_state, solution_index=0),
                common_results=all_results[-4:],
                user_results=all_results[:-4],
                personal_result_index=personal_result_index,
                final_result=SolutionReference(state=this_state, solution_index=0),
            )
        )

        groupiter = groupiter.parent.parent

    # We're at the root, so add the initialization stuff
    if groupiter is not None and groupiter.parent is None:
        this_state = session.exec(select(StateDB).where(StateDB.id == groupiter.state_id)).first()

        if this_state is None:
            raise HTTPException(detail="Initialization state does not exist!", status_code=status.HTTP_404_NOT_FOUND)

        full_iterations.append(
            FullIteration(
                phase="init",
                optimization_preferences=None,
                voting_preferences=None,
                starting_result=None,
                common_results=[],
                user_results=[],
                personal_result_index=None,
                final_result=SolutionReference(state=this_state, solution_index=0),
            )
        )

    return GNIMBUSAllIterationsResponse(all_full_iterations=full_iterations)


@router.post("/toggle_phase")
async def switch_phase(
    request: GNIMBUSSwitchPhaseRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GNIMBUSSwitchPhaseResponse:
    """Switch the phase from one to another. "learning", "crp", "decision" phases are allowed."""
    if request.new_phase not in ["learning", "crp", "decision"]:
        raise HTTPException(
            detail=f"Undefined phase: {request.new_phase}! Can only be {['learning', 'crp', 'decision']}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found", status_code=status.HTTP_404_NOT_FOUND)

    if user.id is not group.owner_id:
        raise HTTPException(detail="Unauthorized user.", status_code=status.HTTP_401_UNAUTHORIZED)

    iteration = group.head_iteration
    if iteration is None:
        raise HTTPException(
            detail="There's no iterations! Did you forget to initialize the problem?",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if iteration.preferences is None:
        raise HTTPException(details="Now this is a funky problem!", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if iteration.preferences.method == "voting":
        raise HTTPException(
            detail="You cannot switch the phase in the middle of the iteration.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    old_phase = iteration.preferences.phase
    new_phase = request.new_phase

    preferences = copy.deepcopy(iteration.preferences)
    preferences.phase = new_phase

    iteration.preferences = preferences
    session.add(iteration)
    session.commit()
    session.refresh(iteration)

    # get the group manager and notify the connected users that the phase has changed
    gman = await manager.get_group_manager(group_id=group.id, method="gnimbus")

    await gman.broadcast(f"The phase was changed from {old_phase} to {new_phase}.")

    return GNIMBUSSwitchPhaseResponse(old_phase=old_phase, new_phase=new_phase)


@router.post("/get_phase")
def get_phase(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Get the current phase of the group."""
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found", status_code=status.HTTP_404_NOT_FOUND)

    g = group.user_ids
    g.append(group.owner_id)

    if user.id not in g:
        raise HTTPException(detail="Unauthorized user.", status_code=status.HTTP_401_UNAUTHORIZED)

    current_iteration = group.head_iteration
    if current_iteration is None:
        raise not_init_error

    if current_iteration.preferences.method != "optimization":
        current_iteration = current_iteration.parent

    return JSONResponse(content={"phase": current_iteration.preferences.phase}, status_code=status.HTTP_200_OK)
