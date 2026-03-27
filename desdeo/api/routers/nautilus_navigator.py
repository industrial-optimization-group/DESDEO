"""New NAUTILUS Navigator endpoints (state-based design)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from desdeo.api.db import get_session
from desdeo.api.db_models import Problem as ProblemInDB
from desdeo.api.models import StateDB
from desdeo.api.models.nautilus_navigator import (
    NautilusNavigatorInitializationState,
    NautilusNavigatorNavigationState,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.schema import User
from desdeo.api.schemas.nautilus import (
    NautilusInitialResponse,
    NautilusInitRequest,
    NautilusNavigateRequest,
    NautilusNavigateResponse,
    NautilusStep,
)
from desdeo.mcdm.nautilus_navigator import (
    NAUTILUS_Response,
    navigator_all_steps,
    navigator_init,
)
from desdeo.problem.schema import Problem

router = APIRouter(prefix="/nautilus", tags=["NAUTILUS Navigator"])

def map_response_to_step(response: NAUTILUS_Response) -> NautilusStep:
    """Helper function to map response to a specific step."""
    reachable_bounds = response.reachable_bounds or {}

    return NautilusStep(
        step_number=response.step_number,
        navigation_point=response.navigation_point,
        lower_bounds=reachable_bounds.get("lower_bounds", {}),
        upper_bounds=reachable_bounds.get("upper_bounds", {}),
        reachable_solution=response.reachable_solution,
        reference_point=response.reference_point,
        bounds=response.bounds,
        distance_to_front=response.distance_to_front,
    )

@router.post("/initialize", response_model=NautilusInitialResponse)
def initialize_navigator(
    request: NautilusInitRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> NautilusInitialResponse:
    """Initialize NAUTILUS Navigator."""
    # --- Validate problem ---
    problem_db = db.query(ProblemInDB).filter(ProblemInDB.id == request.problem_id).first()

    if problem_db is None:
        raise HTTPException(status_code=404, detail="Problem not found.")
    if problem_db.owner != user.id and problem_db.owner is not None:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    # Remove forbidden fields manually for validation
    raw_value = problem_db.value.copy()
    raw_value.pop("is_convex_", None)
    raw_value.pop("is_linear_", None)
    raw_value.pop("is_twice_differentiable_", None)

    try:
        problem = Problem.model_validate(raw_value)
        # problem = Problem.model_validate(problem.value)
    except ValidationError:
        raise HTTPException(status_code=500, detail="Invalid problem format.")  # noqa: B904

    # --- Run algorithm ---
    response = navigator_init(problem)

    # --- Create state properly via StateDB ---
    substate = NautilusNavigatorInitializationState()

    state_row = StateDB.create(
        database_session=db,
        problem_id=problem_db.id,
        state=substate,
        session_id=user.active_session_id,  # or None if not used
    )
    db.commit()
    db.refresh(state_row)

    # --- Map bounds ---
    reachable_bounds = response.reachable_bounds or {}

    return NautilusInitialResponse(
        state_id=state_row.base_state.id,
        parent_state_id=None,
        navigation_point=response.navigation_point,
        lower_bounds=reachable_bounds.get("lower_bounds", {}),
        upper_bounds=reachable_bounds.get("upper_bounds", {}),
        step_number=response.step_number,
        distance_to_front=response.distance_to_front,
    )

@router.post("/navigate", response_model=NautilusNavigateResponse)
def navigate_navigator(
    request: NautilusNavigateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> NautilusNavigateResponse:
    """Perform NAUTILUS navigation steps."""
    problem_db = db.query(ProblemInDB).filter(ProblemInDB.id == request.problem_id).first()

    if problem_db is None:
        raise HTTPException(status_code=404, detail="Problem not found.")
    if problem_db.owner != user.id and problem_db.owner is not None:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    raw_value = problem_db.value.copy()
    raw_value.pop("is_convex_", None)
    raw_value.pop("is_linear_", None)
    raw_value.pop("is_twice_differentiable_", None)

    try:
        problem = Problem.model_validate(raw_value)
    except ValidationError:
        raise HTTPException(status_code=500, detail="Invalid problem format.")  # noqa: B904

    last_nav_state = (
        db.query(NautilusNavigatorNavigationState)
        .order_by(NautilusNavigatorNavigationState.id.desc())
        .first()
    )
    parent_state_id = last_nav_state.id if last_nav_state else None

    previous_responses: list[NAUTILUS_Response] = []
    current = last_nav_state
    while current:
        previous_responses = [
            NAUTILUS_Response.model_validate(r) for r in current.navigator_results
        ] + previous_responses
        if getattr(current, "parent_state_id", None):
            current = db.query(NautilusNavigatorNavigationState).filter(
                NautilusNavigatorNavigationState.id == current.parent_state_id
            ).first()
        else:
            current = None

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
        raise HTTPException(status_code=400, detail="Bounds are too restrictive.") from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))  # noqa: B904

    substate = NautilusNavigatorNavigationState(
        steps_remaining=request.steps_remaining,
        reference_point=request.reference_point,
        bounds=request.bounds,
        previous_responses=[r.model_dump(mode="json") for r in previous_responses],
        navigator_results=[r.model_dump(mode="json") for r in new_responses],
        parent_state_id=parent_state_id,
    )

    state_row = StateDB.create(
        database_session=db,
        problem_id=problem_db.id,
        state=substate,
        session_id=user.active_session_id,
        parent_id=parent_state_id,
    )

    db.commit()
    db.refresh(state_row)


    steps = [map_response_to_step(r) for r in new_responses]

    return NautilusNavigateResponse(
        state_id=state_row.base_state.id,
        parent_state_id=parent_state_id,
        steps=steps,
    )
