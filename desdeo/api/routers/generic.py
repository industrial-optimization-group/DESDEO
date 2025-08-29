"""Defines end-points to access generic functionalities."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    InteractiveSessionDB,
    IntermediateSolutionRequest,
    IntermediateSolutionState,
    ProblemDB,
    StateDB,
    User,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.nimbus import solve_intermediate_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults

router = APIRouter(prefix="/method/generic")


@router.post("/intermediate")
def solve_intermediate(
    request: IntermediateSolutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> tuple[IntermediateSolutionState, int]:
    """Solve intermediate solutions between given two solutions."""
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

    problem = Problem.from_problemdb(problem_db)
    # Get complete solution information from database using the SolutionAddress
    # For solution 1
    solution1_state_id = request.reference_solution_1.address_state
    solution1_result_index = request.reference_solution_1.address_result
    
    # For solution 2
    solution2_state_id = request.reference_solution_2.address_state
    solution2_result_index = request.reference_solution_2.address_result
    
    # Query the database for the states
    solution1_state = session.exec(select(StateDB).where(StateDB.id == solution1_state_id)).first()
    solution2_state = session.exec(select(StateDB).where(StateDB.id == solution2_state_id)).first()
    
    if not solution1_state or not solution2_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find one or both of the referenced solution states"
        )
    
    if not hasattr(solution1_state.state, 'solver_results') or not hasattr(solution2_state.state, 'solver_results'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or both of the referenced states do not contain solver results"
        )
    
    # Extract the full solution information including variables
    try:
        solution1_full = solution1_state.state.solver_results[solution1_result_index]
        solution2_full = solution2_state.state.solver_results[solution2_result_index]
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referenced solution result index is out of bounds"
        )
    
    # Get solution variables
    solution_1 = solution1_full.optimal_variables
    solution_2 = solution2_full.optimal_variables

    solver_results: list[SolverResults] = solve_intermediate_solutions(
        problem=problem,
        solution_1=solution_1,
        solution_2=solution_2,
        num_desired=request.num_desired,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
    )

    # fetch parent state
    if request.parent_state_id is None:
        # parent state is assumed to be the last state added to the session.
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

    intermediate_state = IntermediateSolutionState(
        scalarization_options=request.scalarization_options,
        context=request.context,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        num_desired=request.num_desired,
        reference_solution_1=request.reference_solution_1.objective_values,
        reference_solution_2=request.reference_solution_2.objective_values,
    )

    # create DB state and add it to the DB
    state = StateDB(
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=intermediate_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return intermediate_state, state.id
