"""A test router for the DESDEO API."""

from typing import Annotated

from fastapi import APIRouter, Depends

from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.schema import User, GuestUser

router = APIRouter(prefix="/test")


@router.get("/userdetails")
def get_user(current_user: Annotated[User, Depends(get_current_user)]) -> User | GuestUser:
    """Get information about the current user."""
    return current_user
