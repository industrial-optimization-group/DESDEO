"""Defines end-points to access and manage problems."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from desdeo.api.db import get_session
from desdeo.api.models import (
    ProblemDB,
    ProblemGetRequest,
    ProblemInfo,
    ProblemInfoSmall,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user

router = APIRouter(prefix="/problem")


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
