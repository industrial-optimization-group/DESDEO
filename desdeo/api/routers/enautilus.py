"""Defines end-points to access functionalities related to the E-NAUTILUS method."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from desdeo.api.db import get_session
from desdeo.api.models import (
    ENautilusState,
    EnautilusStepRequest,
    InteractiveSessionDB,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.problem import Problem

from .utils import fetch_interactive_session, fetch_user_problem

router = APIRouter(prefix="/method/enautilus")


@router.post("/step")
def step(
    request: EnautilusStepRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> ENautilusState:
    """."""
    interactive_session: InteractiveSessionDB | None = fetch_interactive_session(user, request, db_session)
    problem: Problem = fetch_user_problem(user, request, db_session)
