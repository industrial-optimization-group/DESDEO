"""Defines end-points to access and manage interactive sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    CreateSessionRequest,
    GetSessionRequest,
    InteractiveSessionDB,
    InteractiveSessionInfo,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user

router = APIRouter(prefix="/session")


@router.post("/new")
def create_new_session(
    request: CreateSessionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> InteractiveSessionInfo:
    """."""
    interactive_session = InteractiveSessionDB(user_id=user.id, info=request.info)

    session.add(interactive_session)
    session.commit()
    session.refresh(interactive_session)

    user.active_session_id = interactive_session.id

    session.add(user)
    session.commit()
    session.refresh(interactive_session)

    return interactive_session


@router.post("/get")
def get_session(
    request: GetSessionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> InteractiveSessionInfo:
    """Return an interactive session with a given id for the current user.

    Args:
        request (GetSessionRequest): a request containing the id of the session.
        user (Annotated[User, Depends): the current user.
        session (Annotated[Session, Depends): the database session.

    Raises:
        HTTPException: could not find an interactive session with the given id
            for the current user.

    Returns:
        InteractiveSessionInfo: info on the requested interactive session.
    """
    statement = select(InteractiveSessionDB).where(
        InteractiveSessionDB.id == request.session_id, InteractiveSessionDB.user_id == user.id
    )
    result = session.exec(statement)

    interactive_session = result.first()

    if interactive_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find interactive session with id={request.session_id}.",
        )

    return interactive_session
