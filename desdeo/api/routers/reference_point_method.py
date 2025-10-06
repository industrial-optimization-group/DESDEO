"""Defines end-points to access functionalities related to the reference point method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

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
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.routers.problem import check_solver
from desdeo.mcdm import rpm_solve_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults

router = APIRouter(prefix="/method/rpm")


@router.post("/solve")
def solve_solutions(
    request: RPMSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> RPMState:
    """."""

    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == request.session_id)
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == user.active_session_id)

        interactive_session = session.exec(statement).first()

    # fetch the problem from the DB
    statement = select(ProblemDB).where(ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id)
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem with id={request.problem_id} could not be found."
        )

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

    # fetch parent state
    if request.parent_state_id is None:
        # parent state is assumed to be the last sate added to the session.
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )

    else:
        # request.parent_state_id is not None
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find state with id={request.parent_state_id}"
            )

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
