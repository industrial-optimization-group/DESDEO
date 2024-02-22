"""Endpoints for NAUTILUS Navigator."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from desdeo.api.db import get_db
from desdeo.api.db_models import Problem as ProblemInDB
from desdeo.api.db_models import Results
from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.schema import User
from desdeo.mcdm.nautilus_navigator import (
    NAUTILUS_Response,
    get_current_path,
    navigator_all_steps,
    navigator_init,
    step_back_index,
)
from desdeo.problem.schema import Problem

router = APIRouter(prefix="/nautnavi")


class Response(BaseModel):
    """The response from most NAUTILUS Navigator endpoints.

    Contains information about the full navigation process.
    """

    objective_names: list[str] = Field(description="The names of the objectives.")
    is_maximized: list[bool] = Field(description="Whether the objectives are to be maximized or minimized.")
    ideal: list[float] = Field(description="The ideal values of the objectives.")
    nadir: list[float] = Field(description="The nadir values of the objectives.")
    lower_bounds: dict[str, list[float]] = Field(description="The lower bounds of the reachable region.")
    upper_bounds: dict[str, list[float]] = Field(description="The upper bounds of the reachable region.")
    preferences: dict[str, list[float]] = Field(description="The preferences used in each step.")
    # bounds: list[list[float]] = Field(description="The bounds of the reachable region.")
    total_steps: int = Field(description="The total number of steps in the NAUTILUS Navigator.")
    reachable_solution: dict = Field(description="The solution reached at the end of navigation.")


class InitialResponse(BaseModel):
    """The response from the initial endpoint of NAUTILUS Navigator."""

    objective_names: list[str] = Field(description="The names of the objectives.")
    is_maximized: list[bool] = Field(description="Whether the objectives are to be maximized or minimized.")
    ideal: list[float] = Field(description="The ideal values of the objectives.")
    nadir: list[float] = Field(description="The nadir values of the objectives.")
    total_steps: int = Field(description="The total number of steps in the NAUTILUS Navigator.")


class InitRequest(BaseModel):
    """The request to initialize the NAUTILUS Navigator."""

    problem_id: int = Field(description="The ID of the problem to navigate.")


class NavigateRequest(BaseModel):
    """The request to navigate the NAUTILUS Navigator."""

    problem_id: int = Field(description="The ID of the problem to navigate.")
    preference: dict[str, float] = Field(description="The preference of the DM.")
    go_back_step: int = Field(description="The step index to go back.")
    steps_remaining: int = Field(description="The number of steps remaining. Should be total_steps - go_back_step.")


@router.post("/initialize")
def init_navigator(
    init_request: InitRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InitialResponse:
    """Initialize the NAUTILUS Navigator.

    Args:
        init_request (InitRequest): The request to initialize the NAUTILUS Navigator.
        user (Annotated[User, Depends(get_current_user)]): The current user.
        db (Annotated[Session, Depends(get_db)]): The database session.

    Returns:
        InitialResponse: The initial response from the NAUTILUS Navigator.
    """
    problem_id = init_request.problem_id
    problem = db.query(ProblemInDB).filter(ProblemInDB.id == problem_id).first()

    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found.")
    if problem.owner != user.index and problem.owner is not None:
        raise HTTPException(status_code=403, detail="Unauthorized to access chosen problem.")
    try:
        problem = Problem.model_validate(problem.value)
    except ValidationError:
        raise HTTPException(status_code=500, detail="Error in parsing the problem.") from ValidationError

    response = navigator_init(problem)

    # Get and delete all Results from previous runs of NAUTILUS Navigator
    results = db.query(Results).filter(Results.problem == problem_id).filter(Results.user == user.index).all()
    for result in results:
        db.delete(result)
    db.commit()

    new_result = Results(
        user=user.index,
        problem=problem_id,
        value=response.model_dump(mode="json"),
    )
    db.add(new_result)
    db.commit()

    return InitialResponse(
        objective_names=[obj.name for obj in problem.objectives],
        is_maximized=[obj.maximize for obj in problem.objectives],
        ideal=[obj.ideal for obj in problem.objectives],
        nadir=[obj.nadir for obj in problem.objectives],
        total_steps=100,
    )


@router.post("/navigate")
def navigate(
    request: NavigateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Navigate the NAUTILUS Navigator.

    Runs the entire navigation process.

    Args:
        request (NavigateRequest): The request to navigate the NAUTILUS Navigator.

    Raises:
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        Response: _description_
    """
    problem_id, preference, go_back_step, steps_remaining = (
        request.problem_id,
        request.preference,
        request.go_back_step,
        request.steps_remaining,
    )
    problem = db.query(ProblemInDB).filter(ProblemInDB.id == problem_id).first()
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found.")
    if problem.owner != user.index and problem.owner is not None:
        raise HTTPException(status_code=403, detail="Unauthorized to access chosen problem.")
    try:
        problem = Problem.model_validate(problem.value)
    except ValidationError:
        raise HTTPException(status_code=500, detail="Error in parsing the problem.") from ValidationError

    results = db.query(Results).filter(Results.problem == problem_id).filter(Results.user == user.index).all()
    if not results:
        raise HTTPException(status_code=404, detail="NAUTILUS Navigator not initialized.")

    responses = [NAUTILUS_Response.model_validate(result.value) for result in results]

    responses.append(responses[step_back_index(responses, go_back_step)])

    new_responses = navigator_all_steps(
        problem, steps_remaining=steps_remaining, reference_point=preference, previous_responses=responses
    )

    for response in new_responses:
        new_result = Results(
            user=user.index,
            problem=problem_id,
            value=response.model_dump(mode="json"),
        )
        db.add(new_result)
    db.commit()

    responses = [*responses, *new_responses]
    current_path = get_current_path(responses)
    active_responses = [responses[i] for i in current_path]
    lower_bounds = {}
    upper_bounds = {}
    preferences = {}
    for obj in problem.objectives:
        lower_bounds[obj.name] = [response.reachable_bounds["lower_bounds"][obj.name] for response in active_responses]
        upper_bounds[obj.name] = [response.reachable_bounds["upper_bounds"][obj.name] for response in active_responses]
        preferences[obj.name] = [response.reference_point[obj.name] for response in active_responses[1:]]

    return Response(
        objective_names=[obj.name for obj in problem.objectives],
        is_maximized=[obj.maximize for obj in problem.objectives],
        ideal=[obj.ideal for obj in problem.objectives],
        nadir=[obj.nadir for obj in problem.objectives],
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        preferences=preferences,
        total_steps=len(responses) - 1,
        reachable_solution=active_responses[-1].reachable_solution,
    )