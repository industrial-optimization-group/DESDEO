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
    EndProcessPreference,
    FullIteration,
    GNIMBUSAllIterationsResponse,
    GNIMBUSResultResponse,
    GNIMBUSSwitchPhaseRequest,
    GNIMBUSSwitchPhaseResponse,
    GNIMBUSVotingState,
    Group,
    GroupInfoRequest,
    GroupIteration,
    GroupRevertRequest,
    OptimizationPreference,
    ProblemDB,
    SolutionReference,
    SolutionReferenceLite,
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

router = APIRouter(prefix="/gnimbus", tags=["GNIMBUS"])


@router.post("/initialize")
def gnimbus_initialize(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Initialize the problem for GNIMBUS."""
    #Check that all pre-conditions are all right
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found!", status_code=status.HTTP_404_NOT_FOUND)
    if not (user.id in group.user_ids or user.id is group.owner_id):
        raise HTTPException(detail="Unauthorized user", status_code=status.HTTP_401_UNAUTHORIZED)

    head_iteration = session.exec(select(GroupIteration)
                                  .where(GroupIteration.id == group.head_iteration_id)).first()
    if head_iteration is not None:
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

    # Create init state
    state = StateDB.create(
        database_session=session, problem_id=problem_db.id, session_id=None, parent_id=None, state=gnimbus_state
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    # The starting iteration
    start_iteration = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        preferences=VotingPreference(
            set_preferences={},
        ),
        notified={},
        state_id=state.id,
        parent_id=None,
        parent=None,
    )

    session.add(start_iteration)
    session.commit()
    session.refresh(start_iteration)

    # New iteration for continuing; to this we add new preferences and begin building a linked list
    new_iteration = GroupIteration(
        problem_id=start_iteration.problem_id,
        group_id=start_iteration.group_id,
        preferences=OptimizationPreference(
            set_preferences={},
        ),
        notified={},
        parent_id=start_iteration.id,
        parent=start_iteration,
    )

    session.add(new_iteration)
    session.commit()
    session.refresh(new_iteration)

    children = start_iteration.children.copy()
    children.append(new_iteration)
    start_iteration.children = children
    session.add(start_iteration)
    group.head_iteration_id = new_iteration.id
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

    (OBSOLETE AND OUT OF DATE!)

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

    head_iteration = session.exec(select(GroupIteration)
                                  .where(GroupIteration.id == group.head_iteration_id)).first()

    try:
        iteration = head_iteration.parent
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

    head_iteration = session.exec(select(GroupIteration)
                                  .where(GroupIteration.id == group.head_iteration_id)).first()

    try:
        groupiter = head_iteration.parent
    except Exception as e:
        raise not_init_error from e

    if groupiter is None:
        raise not_init_error

    full_iterations: list[FullIteration] = []

    user_len = len(group.user_ids)

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
            all_results.append(SolutionReferenceLite(state=this_state, solution_index=i))

        phase = groupiter.preferences.phase

        full_iterations.append(
            FullIteration(
                phase=phase,
                optimization_preferences=groupiter.preferences,
                voting_preferences=None,
                starting_result=SolutionReferenceLite(state=prev_state, solution_index=0),
                common_results=all_results if phase in ["decision", "compromise"] else all_results[user_len:],
                user_results=all_results[:user_len],
                personal_result_index=personal_result_index,
                final_result=None,
            )
        )

        groupiter = groupiter.parent

    # We're at voting/end method now. Construct an FullIteration item from Voting/Ending an Optimization iterations
    # A bit of a complicated mess, I could have done this in a better manner.
    while groupiter is not None and groupiter.parent is not None and groupiter.parent.parent is not None:
        this_state = session.exec(select(StateDB).where(StateDB.id == groupiter.state_id)).first()
        prev_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.state_id)).first()
        first_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.parent.state_id)).first()

        if this_state is None or prev_state is None or first_state is None:
            raise HTTPException(detail="All needed states do not exist!", status_code=status.HTTP_404_NOT_FOUND)

        all_results = []
        for i, _ in enumerate(prev_state.state.solver_results):
            all_results.append(SolutionReferenceLite(state=prev_state, solution_index=i))

        personal_result_index = None
        for i, item in enumerate(groupiter.parent.preferences.set_preferences.items()):
            if item[0] == user.id:
                personal_result_index = i
                break

        phase = groupiter.parent.preferences.phase

        full_iterations.append(
            FullIteration(
                phase=phase,
                optimization_preferences=groupiter.parent.preferences,
                voting_preferences=groupiter.preferences,
                starting_result=SolutionReferenceLite(state=first_state, solution_index=0),
                common_results=all_results if phase in ["decision", "compromise"] else all_results[user_len:],
                user_results=all_results[:user_len],
                personal_result_index=personal_result_index,
                final_result=SolutionReferenceLite(state=this_state, solution_index=0),
            )
        )

        groupiter = groupiter.parent.parent

    # We're at the root, so add the initialization iteration (essentially empty with just a final result)
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
                final_result=SolutionReferenceLite(state=this_state, solution_index=0),
            )
        )

    return GNIMBUSAllIterationsResponse(all_full_iterations=full_iterations)


@router.post("/toggle_phase")
async def switch_phase(
    request: GNIMBUSSwitchPhaseRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GNIMBUSSwitchPhaseResponse:
    """Switch the phase from one to another. "learning", "crp", "decision" and "compromise" phases are allowed."""
    #Preliminary checks etc.
    if request.new_phase not in ["learning", "crp", "decision", "compromise"]:
        raise HTTPException(
            detail=f"Undefined phase: {request.new_phase}! Can only be {['learning', 'crp', 'decision']}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found", status_code=status.HTTP_404_NOT_FOUND)
    if user.id is not group.owner_id:
        raise HTTPException(detail="Unauthorized user.", status_code=status.HTTP_401_UNAUTHORIZED)
    iteration = session.exec(select(GroupIteration)
                             .where(GroupIteration.id == group.head_iteration_id)).first()
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

    # Set the phase in the preferences
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

    current_iteration= session.exec(select(GroupIteration)
                                    .where(GroupIteration.id == group.head_iteration_id)).first()
    if current_iteration is None:
        raise not_init_error

    if current_iteration.preferences.method != "optimization":
        current_iteration = current_iteration.parent

    return JSONResponse(content={"phase": current_iteration.preferences.phase}, status_code=status.HTTP_200_OK)

def get_preference_item(iteration):
    """Returns an empty preference item for adding preferences; The preferences are the next preferences.

    Args:
        iteration: we consider this iteration and it's preferences.

    Returns:
        Preference item.
    """
    item = iteration.preferences
    if type(item) is OptimizationPreference:
        if item.phase in ["decision", "compromise"]:
            return EndProcessPreference(
                success=None,
                set_preferences={}
            )
        return VotingPreference(
            set_preferences={}
        )
    return OptimizationPreference(
        phase=iteration.parent.preferences.phase if iteration.parent.preferences.phase is not None else "learning",
        set_preferences={},
    )


@router.post("/revert_iteration")
async def revert_iteration(
    request: GroupRevertRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Changes the starting solution of an iteration so in case of emergency the group owner can just change it.

    Args:
        request (GNIMBUSChangeStartingSolutionRequest): The request containing necessary details to fulfill the change.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): The database session.

    Raises:
        HTTPException

    Returns:
        JSONResponse: Response that acknowledges the changes.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if not group:
        raise HTTPException(
            detail=f"No group with ID {request.group_id}!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    if group.owner_id is not user.id:
        raise HTTPException(
            detail="Unauthorized user!",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    current_iteration = session.exec(select(GroupIteration)
                                     .where(GroupIteration.id == group.head_iteration_id)).first()

    if not current_iteration:
        raise HTTPException(
            detail="There's no head iteration",
            status_code=status.HTTP_404_NOT_FOUND
        )
    head_iteration_type = type(current_iteration.preferences)
    if head_iteration_type in [VotingPreference, EndProcessPreference]:
        raise HTTPException(
            detail="Complete the iteration before reverting. Sorry for the inconvenience.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Get the GroupIteration corresponding to the requests state id
    target_iteration = session.exec(select(GroupIteration).where(GroupIteration.state_id == request.state_id)).first()
    if not target_iteration:
        raise HTTPException(
            detail=f"There's no iteration with state ID {request.state_id}!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    target_iteration_type = type(target_iteration.preferences)
    if target_iteration_type == OptimizationPreference:
        raise HTTPException(
            detail="You can only revert to a result of a complete iteration. Sorry for the inconvenience.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # We must "artificially" create some history, so that we can later on fetch stuff seamlessly,
    # without any hiccups or changes to the "all_iterations" endpoint. Essentially we copy two latest
    # iterations to the head of the history.
    new_parent_1 = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        preferences=target_iteration.parent.preferences.model_copy(),
        notified=target_iteration.parent.notified.copy(),
        state_id=target_iteration.parent.state_id,
        parent_id=current_iteration.parent.id,
        parent=current_iteration.parent
    )

    session.add(new_parent_1)
    session.commit()
    session.refresh(new_parent_1)

    new_parent_2 = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        preferences=target_iteration.preferences.model_copy(),
        notified=target_iteration.notified.copy(),
        state_id=target_iteration.state_id,
        parent_id=new_parent_1.id,
        parent=new_parent_1
    )

    session.add(new_parent_2)
    session.commit()
    session.refresh(new_parent_2)

    # New head iteration
    new_head = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        preferences=OptimizationPreference(
            phase=target_iteration.parent.preferences.phase \
                if target_iteration.parent.preferences.phase is not None else "learning",
            set_preferences={}
        ),
        notified={},
        parent_id=new_parent_2.id,
        parent=new_parent_2,
    )

    session.add(new_head)
    session.commit()

    group.head_iteration_id = new_head.id

    session.add(group)
    session.delete(current_iteration)
    session.commit()
    session.refresh(group)

    gman = await manager.get_group_manager(group_id=group.id, method="gnimbus")
    await gman.broadcast("UPDATE: Latest iteration reversed by the group owner!")

    return JSONResponse(
        content={
            "message": "Iteration reversed!",
        },
        status_code=status.HTTP_200_OK
    )
