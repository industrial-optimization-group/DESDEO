"""Endpoints for NAUTILUS Navigator."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from desdeo.api.db import get_db
from desdeo.api.db_models import Problem as ProblemInDB, MethodState
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
from desdeo.api.utils.database import (
    database_dependency,
    select,
)
from .NAUTILUS_navigator import (
    InitRequest,
    NavigateRequest as SingleNavigateRequest,
    InitialResponse,
    Response,
    buildInitResponse,
    buildResponse,
)

router = APIRouter(prefix="/nautnavigroup")


class GroupNavigateRequest(BaseModel):
    """The request to navigate the NAUTILUS Navigator as a group."""

    request_ids: list[int] = Field(description="List of id of saved requests.")
    cached: bool = Field(description="Determine whether to get saved results.", default=False)


@router.post("/save-request")
async def save_request(
    request: SingleNavigateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[database_dependency, Depends()]
) -> dict:
    """Save request to database.

    Args:
        request (SingleNavigateRequest): The request to be saved.
        user (Annotated[User, Depends(get_current_user)]): The current user.
        db (Annotated[database_dependency, Depends()]): The database session.

    Returns:
        dict: Information about the saved request.
    """

    row = MethodState(
      user=user.index,
      problem=request.problem_id,
      value=request.model_dump(mode="json")
    )

    await db.add(row)
    await db.commit()

    return { "id": row.id }


@router.post("/initialize")
def init_navigator(
    init_request: InitRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InitialResponse | Response:
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
    if problem.value is None:
        raise HTTPException(status_code=500, detail="Problem not found.")

    try:
        problem = Problem.model_validate(problem.value)  # Ignore the mypy error here for now.
    except ValidationError:
        raise HTTPException(status_code=500, detail="Error in parsing the problem.") from ValidationError

    # Get all Results from previous runs of NAUTILUS Navigator
    results = db.query(Results).filter(Results.problem == problem_id).all()

    if len(results) > 0:
        if len(results) == 1:
            return buildInitResponse(problem, init_request)
        else:
            responses = [NAUTILUS_Response.model_validate(result.value) for result in results]
            return buildResponse(problem, [*responses])

    else:
        response = navigator_init(problem)

        new_result = Results(
            user=user.index,
            problem=problem_id,
            value=response.model_dump(mode="json"),
        )

        db.add(new_result)
        db.commit()

        return buildInitResponse(problem, init_request)


@router.post("/navigate")
async def navigate(
    navigateRequest: GroupNavigateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[database_dependency, Depends()],
) -> Response:
    """Navigate the NAUTILUS Navigator Group.

    Runs the entire navigation process.

    Args:
        navigateRequest (GroupNavigateRequest): The request to navigate.
        user (Annotated[User, Depends(get_current_user)]): The current user.
        db (Annotated[database_dependency, Depends()]): The database session.

    Returns:
        Response: The result of navigation process
    """

    requestRows = await db.all(select(MethodState).filter(MethodState.id.in_(navigateRequest.request_ids)))
    requests = [SingleNavigateRequest.model_validate(requestRow.value) for requestRow in requestRows]
    request = requests[0]

    problem_id, preference, go_back_step, steps_remaining, bounds = (
        request.problem_id,
        request.preference,
        request.go_back_step,
        request.steps_remaining,
        request.bounds,
    )
    problem = await db.first(select(ProblemInDB).filter_by(id=problem_id))
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found.")

    try:
        problem = Problem.model_validate(problem.value)  # Ignore the mypy error here for now.
    except ValidationError:
        raise HTTPException(status_code=500, detail="Error in parsing the problem.") from ValidationError

    results = await db.all(select(Results).filter_by(problem=problem_id))

    if not results:
        raise HTTPException(status_code=404, detail="NAUTILUS Navigator not initialized.")

    responses = [NAUTILUS_Response.model_validate(result.value) for result in results]

    if not navigateRequest.cached:
        responses.append(responses[step_back_index(responses, go_back_step)])

        try:
            new_responses = navigator_all_steps(
                problem,
                steps_remaining=steps_remaining,
                reference_point=preference,
                previous_responses=responses,
                bounds=bounds,
            )
        except IndexError as e:
            raise HTTPException(status_code=400, detail="Possible reason for error: bounds are too restrictive.") from e

        for response in new_responses:
            new_result = Results(
                user=user.index,
                problem=problem_id,
                value=response.model_dump(mode="json"),
            )
            await db.add(new_result)
        await db.commit()

        responses = [*responses, *new_responses]
    else:
        responses = [*responses]

    return buildResponse(problem, responses)