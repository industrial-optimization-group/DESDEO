"""Defines end-points to access and manage interactive sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session as get_db_session
from desdeo.api.models import (
    CreateSessionRequest,
    GetSessionRequest,
    InteractiveSessionDB,
    InteractiveSessionInfo,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.routers.utils import SessionContext, fetch_interactive_session, get_session_context_without_request

router = APIRouter(prefix="/session")


@router.post("/new")
def create_new_session(
    request: CreateSessionRequest,
    context: Annotated[SessionContext, Depends(get_session_context_without_request)],
) -> InteractiveSessionInfo:
    """Creates a new interactive session."""
    user = context.user
    db_session = context.db_session

    interactive_session = InteractiveSessionDB(
        user_id=user.id,
        info=request.info,
    )

    db_session.add(interactive_session)
    db_session.commit()
    db_session.refresh(interactive_session)

    user.active_session_id = interactive_session.id

    db_session.add(user)
    db_session.commit()

    return interactive_session


@router.get("/get/{session_id}")
def get_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> InteractiveSessionInfo:
    """Return an interactive session with a current user."""
    request = GetSessionRequest(session_id=session_id)
    return fetch_interactive_session(
        user=user,
        request=request,
        session=session,
    )


@router.get("/get_all", status_code=status.HTTP_200_OK)
def get_all_sessions(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[InteractiveSessionInfo]:
    """Return all interactive sessions of the current user."""
    statement = select(InteractiveSessionDB).where(InteractiveSessionDB.user_id == user.id)
    result = session.exec(statement).all()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No interactive sessions found for the user.",
        )

    return result


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> None:
    """Delete an interactive session and all its related states."""
    request = GetSessionRequest(session_id=session_id)

    interactive_session = fetch_interactive_session(
        user=user,
        request=request,
        session=session,
    )  # raises 404 if not found

    try:
        session.delete(interactive_session)
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete interactive session.",
        ) from exc
