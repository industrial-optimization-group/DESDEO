"""A test router for the DESDEO API."""

from typing import Annotated

from fastapi import APIRouter, Depends

from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.schema import User

router = APIRouter(prefix="/test")


@router.get("/userdetails")
def get_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get information about the current user."""
    return current_user
