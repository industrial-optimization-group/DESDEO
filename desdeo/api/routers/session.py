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
from desdeo.api.routers.utils import fetch_interactive_session

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


@router.get("/get/{session_id}")
def get_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> InteractiveSessionInfo:
    """Return an interactive session with a given id for the current user."""
    interactive_session = fetch_interactive_session(
        session_id=session_id,
        user_id=user.id,
        session=session,
    )
    return interactive_session

@router.get("/get_all", status_code=status.HTTP_200_OK)
def get_all_sessions(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[InteractiveSessionInfo]:
    """Return all interactive sessions of the current user."""
    statement = select(InteractiveSessionDB).where(
        InteractiveSessionDB.user_id == user.id
    )
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
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Delete an interactive session and all its related states."""
    interactive_session = fetch_interactive_session(
        session_id=session_id,
        user_id=user.id,
        session=session,
    ) # raises 404 if not found

    try:
        session.delete(interactive_session)
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete interactive session.",
        )