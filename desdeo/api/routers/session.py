"""Defines end-points to access and manage interactive sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session as get_db_session
from desdeo.api.models import (
    CreateSessionRequest,
    InteractiveSessionDB,
    InteractiveSessionInfo,
    User,
    UserRole,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.routers.utils import (
    SessionContext,
    SessionContextGuard,
    fetch_interactive_session_with_role_check,
)

router = APIRouter(prefix="/session")


@router.post("/new")
def create_new_session(
    request: CreateSessionRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
    target_user_id: int | None = None,
) -> InteractiveSessionInfo:
    """Creates a new interactive session.

    If ``target_user_id`` is provided, the session is created on behalf of that user.
    Only analysts and admins may use this parameter.
    """
    user = context.user
    db_session = context.db_session

    if target_user_id is not None:
        if user.role not in (UserRole.analyst, UserRole.admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only analysts and admins may create sessions for other users.",
            )
        target_user = db_session.get(User, target_user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id={target_user_id} not found.",
            )
        owner = target_user
    else:
        owner = user

    interactive_session = InteractiveSessionDB(
        user_id=owner.id,
        info=request.info,
    )

    db_session.add(interactive_session)
    db_session.commit()
    db_session.refresh(interactive_session)

    owner.active_session_id = interactive_session.id

    db_session.add(owner)
    db_session.commit()

    return InteractiveSessionInfo.model_validate(interactive_session)


@router.get("/get/{session_id}")
def get_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> InteractiveSessionInfo:
    """Return an interactive session. Analysts and admins may access any session."""
    return fetch_interactive_session_with_role_check(
        user=user,
        session_id=session_id,
        session=session,
    )


@router.get("/get_all", status_code=status.HTTP_200_OK)
def get_all_sessions(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> list[InteractiveSessionInfo]:
    """Return interactive sessions. Analysts and admins see all users' sessions; others see only their own."""
    if user.role in (UserRole.analyst, UserRole.admin):
        statement = select(InteractiveSessionDB)
    else:
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.user_id == user.id)

    return list(session.exec(statement).all())


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
) -> None:
    """Delete an interactive session and all its related states. Analysts and admins may delete any session."""
    interactive_session = fetch_interactive_session_with_role_check(
        user=user,
        session_id=session_id,
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
