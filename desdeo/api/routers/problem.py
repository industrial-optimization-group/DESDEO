"""Defines end-points to access and manage problems."""

from typing import Annotated
from fastapi import APIRouter, Depends
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.models import User, ProblemDB, ProblemInfo

router = APIRouter(prefix="/problem")


@router.get("/all_problems")
def get_problems(user: Annotated[User, Depends(get_current_user)]) -> list[ProblemDB]:
    return user.problems


@router.get("/all_problems_info")
def get_problems_info(user: Annotated[User, Depends(get_current_user)]) -> list[ProblemInfo]:
    return user.problems
