"""A selection of utilities for handling routers and data therein."""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from desdeo.api.models import (
    EnautilusStepRequest,
    InteractiveSessionDB,
    ProblemDB,
    RPMSolveRequest,
    User,
)
from desdeo.problem import Problem

RequestType = RPMSolveRequest | EnautilusStepRequest


def fetch_interactive_session(user: User, request: RequestType, session: Session) -> InteractiveSessionDB | None:
    """Gets the desired instance of `InteractiveSessionDB`.

    Args:
        user (User): the user whose interactive sessions are to be queried.
        request (RequestType): the request with possibly information on which interactive session to query.
        session (Session): the database session (not to be confused with the interactive session) from
            which the interactive session should be queried.

    Note:
        If no explicit `session_id` is given in `request`, this function will try to fetch the
        currently active interactive session for the `user`, e.g., with id `user.active_session_id`.
        If this is `None`, then the interactive session returned will be `None` as well.

    Raises:
        HTTPException: when an explicit interactive session is requested, but it is not found.

    Returns:
        InteractiveSessionDB | None: an interactive session DB model, or nothing.
    """
    if request.session_id is not None:
        # specific interactive session id is given, try using that
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == request.session_id)
        interactive_session = session.exec(statement)

        if interactive_session is None:
            # Raise if explicitly requested interactive session cannot be found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    elif user.active_session_id is not None:
        # request.session_id is None
        # try to use active session instead

        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == user.active_session_id)

        interactive_session = session.exec(statement).first()

    # At this point interactive_session is either an instance of InteractiveSessionDB or None (which is fine)

    return interactive_session


def fetch_user_problem(user: User, request: RequestType, session: Session) -> Problem:
    """Fetches a user's `Problem` that corresponds to a given `ProblemDB` based on id.

    Args:
        user (User): the user for which the problem is fetched.
        request (RequestType): request containing details of the problem to be fetched (`request.problem_id`).
        session (Session): the database session from which to fetch the problem.

    Raises:
        HTTPException: a problem with the given id (`request.problem_id`) could not be found (404).
        HTTPException: a fetched `ProblemDB` instance could not be converted to an instance of
            `Problem` (500).

    Returns:
        Problem: the instance of `ProblemDB` with the given id transformed into an instance of `Problem`.
    """
    statement = select(ProblemDB).where(ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id)
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem with id={request.problem_id} could not be found."
        )

    # try converting `ProblemDB` -> `Problem`
    try:
        problem = Problem.from_problemdb(problem_db)
    except Exception as e:
        msg = "Exception raised when trying to convert `ProblemDB` -> `Problem`."

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{msg}. Problem was id={request.problem_id}.",
        ) from e

    return problem


def fetch_parent_state(user: User, request: RequestType, session: Session) -> None:
    """."""
