"""New NAUTILUS Navigator endpoints (state-based design)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from desdeo.api.db import get_db
from desdeo.api.db_models import Problem as ProblemInDB
from desdeo.api.models.nautilus import (
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
    db: Annotated[Session, Depends(get_db)],
) -> NautilusInitialResponse:
    """Initialize NAUTILUS Navigator."""
    # --- Validate problem ---
    problem = db.query(ProblemInDB).filter(ProblemInDB.id == request.problem_id).first()

    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found.")
    if problem.owner != user.index and problem.owner is not None:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    try:
        problem = Problem.model_validate(problem.value)
    except ValidationError:
        raise HTTPException(status_code=500, detail="Invalid problem format.")

    # --- Run algorithm ---
    response = navigator_init(problem)

    # --- Create base state (assuming you have a generic State table) ---
    base_state = NautilusNavigatorInitializationState()
    db.add(base_state)
    db.commit()
    db.refresh(base_state)

    # --- Map bounds ---
    reachable_bounds = response.reachable_bounds or {}

    return NautilusInitialResponse(
        state_id=base_state.state_id,
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
    db: Annotated[Session, Depends(get_db)],
) -> NautilusNavigateResponse:
    """Perform NAUTILUS navigation steps."""
    # --- Validate problem ---
    problem = db.query(ProblemInDB).filter(ProblemInDB.id == request.problem_id).first()

    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found.")
    if problem.owner != user.index and problem.owner is not None:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    try:
        problem = Problem.model_validate(problem.value)
    except ValidationError:
        raise HTTPException(status_code=500, detail="Invalid problem format.")


    # --- Determine parent state ---
    parent_state = (
        db.query(NautilusNavigatorNavigationState)
        .order_by(NautilusNavigatorNavigationState.state_id.desc())
        .first()
    )
    parent_state_id = parent_state.state_id if parent_state else None

    # --- Extract previous responses ---
    previous_responses: list[NAUTILUS_Response] = []
    current = parent_state
    while current:
        previous_responses = [
            NAUTILUS_Response.model_validate(r) for r in current.navigator_results
        ] + previous_responses
        if current.parent_state_id:
            current = db.query(NautilusNavigatorNavigationState).filter(
                NautilusNavigatorNavigationState.state_id == current.parent_state_id
            ).first()
        else:
            current = None

    # --- Run algorithm ---
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
        raise HTTPException(status_code=400, detail=str(e))

    # --- Store state ---
    navigation_state = NautilusNavigatorNavigationState(
        steps_remaining=request.steps_remaining,
        reference_point=request.reference_point,
        bounds=request.bounds,
        previous_responses=[r.model_dump(mode="json") for r in previous_responses],
        navigator_results=[r.model_dump(mode="json") for r in new_responses],
        parent_state_id=parent_state_id,
    )

    db.add(navigation_state)
    db.commit()
    db.refresh(navigation_state)

    # --- Map response ---
    steps = [map_response_to_step(r) for r in new_responses]

    return NautilusNavigateResponse(
        state_id=navigation_state.state_id,
        parent_state_id=parent_state_id,
        steps=steps,
    )
