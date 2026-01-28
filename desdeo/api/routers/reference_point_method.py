"""Defines end-points to access functionalities related to the reference point method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from desdeo.api.models import (
    PreferenceDB,
    RPMSolveRequest,
    RPMState,
    StateDB,
)
from desdeo.api.routers.problem import check_solver
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults

from .utils import SessionContext, get_session_context

router = APIRouter(prefix="/method/rpm")


@router.post("/solve")
def solve_solutions(
    request: RPMSolveRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> RPMState:
    """Runs an iteration of the reference point method.

    Args:
        request (RPMSolveRequest): a request with the needed information to run the method.
        user (Annotated[User, Depends): the current user.
        context (Annotated[SessionContext, Depends): the current session context.

    Returns:
        RPMState: a state with information on the results of iterating the reference point method
            once.
    """
    user = context.user
    db_session = context.db_session
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    # ensure problem exists
    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Problem context missing.",
        )

    solver = check_solver(problem_db=problem_db)
    problem = Problem.from_problemdb(problem_db)

    solver_results: list[SolverResults] = rpm_solve_solutions(
        problem,
        request.preference.aspiration_levels,
        request.scalarization_options,
        solver,
        request.solver_options,
    )

    # create DB preference
    preference_db = PreferenceDB(
        user_id=user.id,
        problem_id=problem_db.id,
        preference=request.preference,
    )

    db_session.add(preference_db)
    db_session.commit()
    db_session.refresh(preference_db)

    # create state and add to DB
    rpm_state = RPMState(
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
    )

    # create DB state and add it to the DB
    state = StateDB(
        problem_id=problem_db.id,
        preference_id=preference_db.id,
        session_id=interactive_session.id if interactive_session else None,
        parent_id=parent_state.id if parent_state else None,
        state=rpm_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return rpm_state
