"""Defines end-points to access functionalities related to the NAUTILUS Navigator method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from desdeo.api.models import (
    NautilusNavigatorInitRequest,
    NautilusNavigatorInitResponse,
    NautilusNavigatorNavigateRequest,
    NautilusNavigatorNavigateResponse,
    NautilusNavigatorStep,
    StateDB,
)
from desdeo.api.models.nautilus_navigator import (
    NautilusNavigatorInitializationState,
    NautilusNavigatorNavigationState,
)
from desdeo.mcdm.nautilus_navigator import (
    NAUTILUS_Response,
    navigator_all_steps,
    navigator_init,
)
from desdeo.problem import Problem

from .utils import ContextField, SessionContext, SessionContextGuard

router = APIRouter(prefix="/nautilus", tags=["NAUTILUS Navigator"])


def _map_response_to_step(response: NAUTILUS_Response) -> NautilusNavigatorStep:
    """Map a NAUTILUS_Response to a NautilusNavigatorStep."""
    reachable_bounds = response.reachable_bounds or {}

    return NautilusNavigatorStep(
        step_number=response.step_number,
        navigation_point=response.navigation_point,
        lower_bounds=reachable_bounds.get("lower_bounds", {}),
        upper_bounds=reachable_bounds.get("upper_bounds", {}),
        reachable_solution=response.reachable_solution,
        reference_point=response.reference_point,
        bounds=response.bounds,
        distance_to_front=response.distance_to_front,
    )


@router.post("/initialize")
def initialize_navigator(
    request: NautilusNavigatorInitRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> NautilusNavigatorInitResponse:
    """Initialize NAUTILUS Navigator."""
    db_session = context.db_session
    problem_db = context.problem_db
    problem = Problem.from_problemdb(problem_db)
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    response = navigator_init(problem)

    substate = NautilusNavigatorInitializationState()

    state_db = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=substate,
    )

    db_session.add(state_db)
    db_session.commit()
    db_session.refresh(state_db)

    reachable_bounds = response.reachable_bounds or {}

    return NautilusNavigatorInitResponse(
        state_id=state_db.id,
        navigation_point=response.navigation_point,
        lower_bounds=reachable_bounds.get("lower_bounds", {}),
        upper_bounds=reachable_bounds.get("upper_bounds", {}),
        step_number=response.step_number,
        distance_to_front=response.distance_to_front,
    )


@router.post("/navigate")
def navigate_navigator(
    request: NautilusNavigatorNavigateRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> NautilusNavigatorNavigateResponse:
    """Perform NAUTILUS navigation steps."""
    db_session = context.db_session
    problem_db = context.problem_db
    problem = Problem.from_problemdb(problem_db)
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    # Reconstruct previous responses by walking the StateDB parent chain.
    previous_responses: list[NAUTILUS_Response] = []
    current_state_db = parent_state
    while current_state_db is not None:
        sub = current_state_db.state
        if isinstance(sub, NautilusNavigatorNavigationState):
            previous_responses = [
                NAUTILUS_Response.model_validate(r) for r in sub.navigator_results
            ] + previous_responses
        current_state_db = current_state_db.parent

    if not previous_responses:
        previous_responses = [
            NAUTILUS_Response(
                step_number=0,
                navigation_point=request.reference_point,
                reachable_solution=None,
                reference_point=request.reference_point,
                bounds=request.bounds,
                distance_to_front=0.0,
                reachable_bounds={"lower_bounds": {}, "upper_bounds": {}},
            )
        ]

    try:
        new_responses = navigator_all_steps(
            problem=problem,
            steps_remaining=request.steps_remaining,
            reference_point=request.reference_point,
            previous_responses=previous_responses,
            bounds=request.bounds,
        )
    except IndexError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bounds are too restrictive.") from e

    substate = NautilusNavigatorNavigationState(
        steps_remaining=request.steps_remaining,
        reference_point=request.reference_point,
        bounds=request.bounds,
        previous_responses=[r.model_dump(mode="json") for r in previous_responses],
        navigator_results=[r.model_dump(mode="json") for r in new_responses],
    )

    state_db = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        state=substate,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
    )

    db_session.add(state_db)
    db_session.commit()
    db_session.refresh(state_db)

    steps = [_map_response_to_step(r) for r in new_responses]

    return NautilusNavigatorNavigateResponse(
        state_id=state_db.id,
        steps=steps,
    )
