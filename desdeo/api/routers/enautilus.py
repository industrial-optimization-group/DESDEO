"""Defines end-points to access functionalities related to the E-NAUTILUS method."""

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ENautilusState,
    EnautilusStepRequest,
    InteractiveSessionDB,
    RepresentativeNonDominatedSolutions,
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
    """Steps the E-NAUTILUS method."""
    problem_db: Problem = fetch_user_problem(user, request, db_session)
    problem = Problem.from_problemdb(problem_db)
    interactive_session: InteractiveSessionDB | None = fetch_interactive_session(user, request, db_session)

    representative_solutions = db_session.exec(
        select(RepresentativeNonDominatedSolutions).where(
            RepresentativeNonDominatedSolutions.id == request.representative_solutions_id
        )
    ).first()

    if request.current_iteration == 0:
        selected_point = {
            f"{obj.symbol}": np.max(representative_solutions.solution_data[f"{obj.symbol}_min"])
            for obj in problem.objectives
        }
        reachable_point_indices = []
    else:
        selected_point = request.selected_point
        reachable_point_indices = request.reachable_point_indices
