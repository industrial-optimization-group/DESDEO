"""Endpoints for NAUTILUS 1."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from desdeo.api.db import get_db
from desdeo.api.db_models import Problem as ProblemInDB
from desdeo.api.db_models import Results
from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.schema import User
#TODO: needs these below ! CHANGE TO real function names if different. Following the naming of nautilus1_* instead of navigator_*
from desdeo.mcdm.nautilus1 import (
    NAUTILUS_Response,
    get_current_path,
    nautilus1_all_steps,
    nautilus1_init,
    step_back_index,
)
from desdeo.problem.schema import Problem

router = APIRouter(prefix="/naut1")

class InitRequest(BaseModel):
    """The request to initialize the NAUTILUS 1."""

    problem_id: int = Field(description="The ID of the problem to navigate.")
    # TODO: IS total_steps needed for NAUTILUS 1, what is good default? now its 5.
    total_steps: int | None = Field(
        description=("The total number of steps in the NAUTILUS 1. The default value is 5."), default=5
    )

class NavigateRequest(BaseModel):
    """The request to navigate the NAUTILUS 1."""

    problem_id: int = Field(description="The ID of the problem to navigate.")
    preference: dict[str, float] = Field(description="The preference of the DM.")
    bounds: dict[str, float] = Field(description="The bounds preference of the DM.")
    go_back_step: int = Field(description="The step index to go back.")
    steps_remaining: int = Field(description="The number of steps remaining. Should be total_steps - go_back_step.")

class InitialResponse(BaseModel):
    """The response from the initial endpoint of NAUTILUS 1."""

    objective_names: list[str] = Field(description="The names of the objectives.")
    is_maximized: list[bool] = Field(description="Whether the objectives are to be maximized or minimized.")
    ideal: list[float] = Field(description="The ideal values of the objectives.")
    nadir: list[float] = Field(description="The nadir values of the objectives.")
    total_steps: int = Field(description="The total number of steps in the NAUTILUS 1.")

class Response(BaseModel):
    """The response from most NAUTILUS 1 endpoints.

    Contains information about the full navigation process.
    """

    objective_names: list[str] = Field(description="The names of the objectives.")
    is_maximized: list[bool] = Field(description="Whether the objectives are to be maximized or minimized.")
    ideal: list[float] = Field(description="The ideal values of the objectives.")
    nadir: list[float] = Field(description="The nadir values of the objectives.")
    lower_bounds: dict[str, list[float]] = Field(description="The lower bounds of the reachable region.")
    upper_bounds: dict[str, list[float]] = Field(description="The upper bounds of the reachable region.")
    preferences: dict[str, list[float]] = Field(description="The preferences used in each step.")
    bounds: dict[str, list[float]] = Field(description="The bounds preference of the DM.")
    total_steps: int = Field(description="The total number of steps in the NAUTILUS 1.")
    reachable_solution: dict = Field(description="The solution reached at the end of navigation.")

    # TODO: ALL ABOVE SHOULD BE FINE

@router.post("/initialize")
def init_nautilus1(
    init_request: InitRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InitialResponse:
    """Initialize the NAUTILUS 1.

    Args:
        init_request (InitRequest): The request to initialize the NAUTILUS 1.
        user (Annotated[User, Depends(get_current_user)]): The current user.
        db (Annotated[Session, Depends(get_db)]): The database session.

    Returns:
        InitialResponse: The initial response from the NAUTILUS 1.
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

    # TODO: CHANGE NAME Of inits to the real one.
    response = nautilus1_init(problem)

     # Get and delete all Results from previous runs of NAUTILUS 1
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
        total_steps=init_request.total_steps,
    )


@router.post("/navigate")
def navigate(
    request: NavigateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Navigate the NAUTILUS 1.

    Runs the entire navigation process.

    Args:
        request (NavigateRequest): The request to navigate the NAUTILUS 1.

    Raises:
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        Response: _description_
    """
    problem_id, preference, go_back_step, steps_remaining, bounds = (
        request.problem_id,
        request.preference,
        request.go_back_step,
        request.steps_remaining,
        request.bounds,
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
        raise HTTPException(status_code=404, detail="NAUTILUS 1 not initialized.")

    # TODO: possibly need to change the NAUTILUS_Response object?
    responses = [NAUTILUS_Response.model_validate(result.value) for result in results]

    responses.append(responses[step_back_index(responses, go_back_step)])

    try:
        new_responses = nautilus1_all_steps(
            problem,
            steps_remaining=steps_remaining,
            reference_point=preference, # TODO: is this reference point in NAUTILUS 1 or something else at this point?
            previous_responses=responses,
            bounds=bounds,
        )
    except IndexError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

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
    bounds = {}
    for obj in problem.objectives:
        lower_bounds[obj.name] = [response.reachable_bounds["lower_bounds"][obj.name] for response in active_responses]
        upper_bounds[obj.name] = [response.reachable_bounds["upper_bounds"][obj.name] for response in active_responses]
        preferences[obj.name] = [response.reference_point[obj.name] for response in active_responses[1:]]
        bounds[obj.name] = [response.bounds[obj.name] for response in active_responses[1:]]

    return Response(
        objective_names=[obj.name for obj in problem.objectives],
        is_maximized=[obj.maximize for obj in problem.objectives],
        ideal=[obj.ideal for obj in problem.objectives],
        nadir=[obj.nadir for obj in problem.objectives],
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        bounds=bounds,
        preferences=preferences,
        total_steps=len(active_responses) - 1,
        reachable_solution=active_responses[-1].reachable_solution,
    )