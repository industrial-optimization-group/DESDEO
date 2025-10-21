"""A selection of utilities for handling routers and data therein."""

from fastapi import HTTPException, status
from sqlmodel import Session, select

from desdeo.api.models import (
    EnautilusStepRequest,
    InteractiveSessionDB,
    ProblemDB,
    RPMSolveRequest,
    StateDB,
    User,
)

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
    else:
        # request.session_id is None
        # try to use active session instead

        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == user.active_session_id)

        interactive_session = session.exec(statement).first()

    # At this point interactive_session is either an instance of InteractiveSessionDB or None (which is fine)

    return interactive_session


def fetch_user_problem(user: User, request: RequestType, session: Session) -> ProblemDB:
    """Fetches a user's `ProblemDB` based on the id in the given request.

    Args:
        user (User): the user for which the problem is fetched.
        request (RequestType): request containing details of the problem to be fetched (`request.problem_id`).
        session (Session): the database session from which to fetch the problem.

    Raises:
        HTTPException: a problem with the given id (`request.problem_id`) could not be found (404).

    Returns:
        Problem: the instance of `ProblemDB` with the given id.
    """
    statement = select(ProblemDB).where(ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id)
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem with id={request.problem_id} could not be found."
        )

    return problem_db


def fetch_parent_state(
    user: User, request: RequestType, session: Session, interactive_session: InteractiveSessionDB | None = None
) -> StateDB | None:
    """Fetches the parent state, if an id is given, or if defined in the given interactive session.

    Determines the appropriate parent `StateDB` instance to associate with a new
    state or operation. It first checks whether the `request` explicitly
    provides a `parent_state_id`. If so, it attempts to retrieve the
    corresponding `StateDB` entry from the database. If no such id is provided,
    the function defaults to returning the most recently added state from the
    given `interactive_session`, if available. If neither source provides a
    parent state, `None` is returned.


    Args:
        user (User): the user for which the parent state is fetched.
        request (RequestType): request containing details about the parent state and optionally the
            interactive session.
        session (Session): the database session from which to fetch the parent state.
        interactive_session (InteractiveSessionDB | None, optional): the interactive session containing
            information about the parent state. Defaults to None.

    Raises:
        HTTPException: when `request.parent_state_id` is not `None` and a `StateDB` with this id cannot
            be found in the given database session.

    Returns:
        StateDB | None: if `request.parent_state_id` is given, returns the corresponding `StateDB`.
            If it is not given, returns the latest state defined in `interactive_session.states`.
            If both `request.parent_state_id` and `interactive_session` are `None`, then returns `None`.
    """
    if request.parent_state_id is None:
        # parent state is assumed to be the last sate added to the session.
        # if `interactive_session` is None, then parent state is set to None.
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )

    else:
        # request.parent_state_id is not None
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        # this error is raised because if a parent_state_id is given, it is assumed that the
        # user wished to use that state explicitly as the parent.
        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find state with id={request.parent_state_id}"
            )

    return parent_state
