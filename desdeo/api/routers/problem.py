"""Defines end-points to access and manage problems."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ProblemDB,
    ProblemGetRequest,
    ProblemInfo,
    ProblemInfoSmall,
    User,
    UserRole,
    ProblemMetaDataGetRequest,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.problem import Problem

router = APIRouter(prefix="/problem")


# This is needed, because otherwise fields ending in an underscore fail to parse.
async def parse_problem_json(request: Request) -> Problem:
    """Helper function to pass by_name=True to model_validate when coercing the json object to a Problem object."""
    data: dict = await request.json()
    return Problem.model_validate(data, by_name=True)


@router.get("/all")
def get_problems(user: Annotated[User, Depends(get_current_user)]) -> list[ProblemInfoSmall]:
    """Get information on all the current user's problems.

    Args:
        user (Annotated[User, Depends): the current user.

    Returns:
        list[ProblemInfoSmall]: a list of information on all the problems.
    """
    return user.problems


@router.get("/all_info")
def get_problems_info(user: Annotated[User, Depends(get_current_user)]) -> list[ProblemInfo]:
    """Get detailed information on all the current user's problems.

    Args:
        user (Annotated[User, Depends): the current user.

    Returns:
        list[ProblemInfo]: a list of the detailed information on all the problems.
    """
    return user.problems


@router.post("/get")
def get_problem(
    request: ProblemGetRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ProblemInfo:
    """Get the model of a specific problem.

    Args:
        request (ProblemGetRequest): the request containing the problem's id `problem_id`.
        user (Annotated[User, Depends): the current user.
        session (Annotated[Session, Depends): the database session.

    Raises:
        HTTPException: could not find a problem with the given id.

    Returns:
        ProblemInfo: detailed information on the requested problem.
    """
    problem = session.get(ProblemDB, request.problem_id)

    if problem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The problem with the requested id={request.problem_id} was not found.",
        )

    return problem


@router.post("/add")
def add_problem(
    request: Annotated[Problem, Depends(parse_problem_json)],
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ProblemInfo:
    """Add a newly defined problem to the database.

    Args:
        request (Problem): the JSON representation of the problem.
        user (Annotated[User, Depends): the current user.
        session (Annotated[Session, Depends): the database session.

    Note:
        Users with the role 'guest' may not add new problems.

    Raises:
        HTTPException: when any issue with defining the problem arises.

    Returns:
        ProblemInfo: the information about the problem added.
    """
    if user.role == UserRole.guest:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest users are not allowed to add new problems."
        )
    try:
        problem_db = ProblemDB.from_problem(request, user=user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not add problem. Possible reason: {e!r}",
        ) from e

    session.add(problem_db)
    session.commit()
    session.refresh(problem_db)

    return problem_db


@router.post("/get_metadata")
def get_metadata(
    request: ProblemMetaDataGetRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[Any]:
    """Fetch specific metadata for a specific problem. See all the possible metadata types from DESDEO/desdeo/api/models/problem.py Problem Metadata section.

    Args:
        request (MetaDataGetRequest): requesting certain problem's certain metadata
        user (Annotated[User, Depends]): the current user
        session (Annotated[Session, Depends]): the database session

    Returns:
        list[Any] | None: list of all forest metadata for this problem, or nothing if there's nothing
    """
    statement = select(ProblemDB).where(ProblemDB.id == request.problem_id)
    problem_from_db = session.exec(statement).first()
    if problem_from_db == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {request.problem_id} not found!"
        )
    problem_metadata = problem_from_db.problem_metadata
    if problem_metadata == None:
        return []
    return [metadata for metadata in problem_metadata.data if metadata.metadata_type == request.metadata_type]
