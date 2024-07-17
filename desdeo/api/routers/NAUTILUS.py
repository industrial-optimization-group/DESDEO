"""Endpoints for NAUTILUS ."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from desdeo.api.db import get_db
from desdeo.api.db_models import Problem as ProblemInDB
from desdeo.api.db_models import Results
from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.schema import User
from desdeo.mcdm.nautilus import (
    NAUTILUS_Response,
    get_current_path,
    nautilus_init,
    nautilus_step,
    points_to_weights,
    ranks_to_weights,
    step_back_index,
)
from desdeo.problem.schema import Problem

router = APIRouter(prefix="/nautilus")


class InitRequest(BaseModel):
    """The request to initialize the NAUTILUS."""

    problem_id: int = Field(description="The ID of the problem to navigate.")
    # TODO: IS total_steps needed for NAUTILUS, what is good default? now its 5.
    total_steps: int | None = Field(
        description=("The total number of steps in the NAUTILUS. The default value is 5."), default=5
    )


class NavigateRequest(BaseModel):
    """The request to navigate the NAUTILUS."""

    problem_id: int = Field(description="The ID of the problem to navigate.")
    points: dict[str, float] | None = Field(
        description=(
            "Preference in the form of points given to the objectives."
            " Higher is better. Must sum up to 100. Only one of points or ranks can be given."
        )
    )
    ranks: dict[str, int] | None = Field(
        description=(
            "Preference in the form of ranks given to the objectives. Higher is better."
            "Must be integers between 1 and the number of objectives. Ranks need not be unique, consecutive."
        )
    )
    calculate_step: int = Field(description="The step index to calculate. Starts from 1. Max = total_steps.")
    steps_remaining: int = Field(
        description="The number of steps remaining. Should be total_steps - calculate_step + 1."
    )


class InitialResponse(BaseModel):
    """The response from the initial endpoint of NAUTILUS."""

    objective_symbols: list[str] = Field(description="The symbols/short names of the objectives.")
    objective_long_names: list[str] = Field(description="Long/descriptive names of the objectives.")
    units: list[str] | None = Field(description="The units of the objectives.")
    is_maximized: list[bool] = Field(description="Whether the objectives are to be maximized or minimized.")
    ideal: list[float] = Field(description="The ideal values of the objectives.")
    nadir: list[float] = Field(description="The nadir values of the objectives.")
    total_steps: int = Field(description="The total number of steps in the NAUTILUS Navigator.")
    distance_to_front: float | None = Field(description="The distance to the front of the reachable region.")


class Response(InitialResponse):
    """The response from most NAUTILUS endpoints.

    Contains information about the full navigation process.
    """

    lower_bounds: dict[str, list[float]] = Field(description="The lower bounds of the reachable region.")
    upper_bounds: dict[str, list[float]] = Field(description="The upper bounds of the reachable region.")
    preferences: dict[str, list[float]] = Field(description="The preferences used in each step.")

    # TODO: ALL ABOVE SHOULD BE FINE


@router.post("/initialize")
def init_nautilus(
    init_request: InitRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InitialResponse:
    """Initialize the NAUTILUS.

    Args:
        init_request (InitRequest): The request to initialize the NAUTILUS.
        user (Annotated[User, Depends(get_current_user)]): The current user.
        db (Annotated[Session, Depends(get_db)]): The database session.

    Returns:
        InitialResponse: The initial response from the NAUTILUS.
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

    response = nautilus_init(problem)

    # Get and delete all Results from previous runs of NAUTILUS
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
        objective_symbols=[obj.symbol for obj in problem.objectives],
        objective_long_names=[obj.name for obj in problem.objectives],
        units=[obj.unit for obj in problem.objectives],
        is_maximized=[obj.maximize for obj in problem.objectives],
        ideal=[obj.ideal for obj in problem.objectives],
        nadir=[obj.nadir for obj in problem.objectives],
        total_steps=init_request.total_steps,
        distance_to_front=response.distance_to_front,
    )


@router.post("/iterate")
def iterate(
    request: NavigateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Navigate the NAUTILUS.

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
    problem_id, ranks, points, calculate_step, steps_remaining = (
        request.problem_id,
        request.ranks,
        request.points,
        request.calculate_step,
        request.steps_remaining,
    )

    if ranks is not None and points is not None:
        raise HTTPException(status_code=400, detail="Both ranks and points cannot be given.")
    if ranks is None and points is None:
        raise HTTPException(status_code=400, detail="Either ranks or points must be given.")

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

    responses = [NAUTILUS_Response.model_validate(result.value) for result in results]

    step_to_append_index = step_back_index(responses, calculate_step - 1)

    if step_to_append_index < len(responses) - 1:
        responses.append(responses[step_back_index(responses, calculate_step - 1)])

    try:
        new_response = nautilus_step(
            problem,
            step_number=calculate_step,
            steps_remaining=steps_remaining,
            nav_point=responses[-1].navigation_point,
            ranks=ranks,
            points=points,
        )
    except IndexError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    new_result = Results(
        user=user.index,
        problem=problem_id,
        value=new_response.model_dump(mode="json"),
    )
    db.add(new_result)
    db.commit()

    responses = [*responses, new_response]
    current_path = get_current_path(responses)
    active_responses = [responses[i] for i in current_path]
    lower_bounds = {}
    upper_bounds = {}
    preferences = {}
    for obj in problem.objectives:
        lower_bounds[obj.symbol] = [response.reachable_bounds["lower_bounds"][obj.symbol] for response in active_responses]
        upper_bounds[obj.symbol] = [response.reachable_bounds["upper_bounds"][obj.symbol] for response in active_responses]
        preferences[obj.symbol] = [response.preference[obj.symbol] for response in active_responses[1:]]

    return Response(
        objective_symbols=[obj.symbol for obj in problem.objectives],
        objective_long_names=[obj.name for obj in problem.objectives],
        units=[obj.unit for obj in problem.objectives],
        is_maximized=[obj.maximize for obj in problem.objectives],
        ideal=[obj.ideal for obj in problem.objectives],
        nadir=[obj.nadir for obj in problem.objectives],
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        preferences=preferences,
        total_steps=len(active_responses) - 1,
        distance_to_front=active_responses[-1].distance_to_front,
    )
