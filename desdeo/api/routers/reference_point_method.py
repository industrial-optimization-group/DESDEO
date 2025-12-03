"""Defines end-points to access functionalities related to the reference point method."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from desdeo.api.db import get_session
from desdeo.api.models import (
    InteractiveSessionDB,
    PreferenceDB,
    ProblemDB,
    RPMSolveRequest,
    RPMState,
    StateDB,
    User,
)
from desdeo.api.routers.problem import check_solver
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults

from .utils import fetch_interactive_session, fetch_parent_state, fetch_user_problem

router = APIRouter(prefix="/method/rpm")


@router.post("/solve")
def solve_solutions(
    request: RPMSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMState:
    """Runs an iteration of the reference point method.

    Args:
        request (RPMSolveRequest): a request with the needed information to run the method.
        user (Annotated[User, Depends): the current user.
        session (Annotated[Session, Depends): the current database session.

    Returns:
        RPMState: a state with information on the results of iterating the reference point method
            once.
    """
    # fetch interactive session, parent state, and ProblemDB
    interactive_session: InteractiveSessionDB = fetch_interactive_session(user, request, session)
    parent_state = fetch_parent_state(user, request, session, interactive_session)

    problem_db: ProblemDB = fetch_user_problem(user, request, session)

    solver = check_solver(problem_db=problem_db)

    problem = Problem.from_problemdb(problem_db)

    # optimize for solutions
    solver_results: list[SolverResults] = rpm_solve_solutions(
        problem,
        request.preference.aspiration_levels,
        request.scalarization_options,
        solver,
        request.solver_options,
    )

    # create DB preference
    preference_db = PreferenceDB(user_id=user.id, problem_id=problem_db.id, preference=request.preference)

    session.add(preference_db)
    session.commit()
    session.refresh(preference_db)

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
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=rpm_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return rpm_state
