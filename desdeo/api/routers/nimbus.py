""" Defines end-points to access functionalities related to the NIMBUS method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from numpy import allclose
from sqlmodel import Session, and_, or_, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    InteractiveSessionDB,
    IntermediateSolutionRequest,
    IntermediateSolutionResponse,
    IntermediateSolutionState,
    NIMBUSClassificationRequest,
    NIMBUSClassificationResponse,
    NIMBUSClassificationState,
    NIMBUSInitializationRequest,
    NIMBUSInitializationResponse,
    NIMBUSInitializationState,
    NIMBUSSaveRequest,
    NIMBUSSaveResponse,
    NIMBUSSaveState,
    PreferenceDB,
    ProblemDB,
    SolutionAddress,
    StateDB,
    User,
    UserSavedSolutionAddress,
    UserSavedSolutionDB,
)
from desdeo.api.routers.generic import solve_intermediate
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.utils.database import user_save_solutions
from desdeo.mcdm.nimbus import generate_starting_point, solve_sub_problems
from desdeo.problem import Problem
from desdeo.tools import SolverResults
from desdeo.tools.gurobipy_solver_interfaces import GurobipySolver

router = APIRouter(prefix="/method/nimbus")

#helper for collecting solutions
def filter_duplicates(
    solutions: list[SolutionAddress]
) -> list[SolutionAddress]:
    """Filters out the duplicate values of objectives."""

    # No solutions or only one solution. There can not be any duplicates.
    if len(solutions) < 2:
        return solutions

    # Get the objective values
    objective_values_list = list(map(lambda sol: sol.objective_values, solutions))
    # Get the function symbols
    objective_keys = [key for key in objective_values_list[0]]
    # Get the corresponding values for functions into a list of lists of values
    valuelists = list(map(lambda dictionary: list(map(lambda key: dictionary[key], objective_keys)), objective_values_list))

    # Check duplicate indices
    duplicate_indices = []
    for i in range(len(solutions) - 1):
        for j in range(i + 1, len(solutions)):
            # If all values of the objective functions are (nearly) identical, that's a duplicate
            if allclose(valuelists[i], valuelists[j]):  # TODO: "similarity tolerance" from problem metadata
                duplicate_indices.append(i)
    
    # Quite the memory hell. See If there's a smarter way to do this
    new_solutions = []
    for i in range(len(solutions)):
        if i not in duplicate_indices:
            new_solutions.append(solutions[i])

    return new_solutions

# for collecting solutions for responses in iterate and initialize endpoints
def collect_saved_solutions(
    user: User,
    problem_id: int,
    session: Session
) -> list[UserSavedSolutionAddress]:
    """Collects all saved solutions for the user and problem."""
    saved_from_db = session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.problem_id == problem_id,
            UserSavedSolutionDB.user_id == user.id
        )
    ).all()

    saved_solutions = []
    for saved_solution in saved_from_db:
        saved_solutions.append(
            UserSavedSolutionAddress(
                objective_values=saved_solution.objective_values,
                address_state=saved_solution.address_state,
                address_result=saved_solution.address_result,
                name=saved_solution.name,
            )
        )

    return filter_duplicates(saved_solutions)

# for collecting solutions for responses in iterate and initialize endpoints
def collect_all_solutions(
    user: User,
    problem_id: int,
    session: Session
) -> list[SolutionAddress]:
    """Collects all solutions for the user and problem."""
    statement = (
    select(StateDB)
    .where(
    or_(
    StateDB.problem_id == problem_id,
    StateDB.preference_id == problem_id
    ),
    StateDB.session_id == user.active_session_id
    )
    .order_by(StateDB.id.desc())
    )
    states = session.exec(statement).all()
    all_solutions = []
    for state in states:
        if state.state is not None and hasattr(state.state, 'solver_results'):
            for i, result in enumerate(state.state.solver_results):
                all_solutions.append(
                    SolutionAddress(
                        objective_values=result.optimal_objectives,
                        address_state=state.id,
                        address_result=i
                    )
                )

    return filter_duplicates(all_solutions)

@router.post("/solve")
def solve_solutions(
    request: NIMBUSClassificationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSClassificationResponse:
    """Solve the problem using the NIMBUS method."""
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

    solver_results: list[SolverResults] = solve_sub_problems(
        problem=problem,
        current_objectives=request.current_objectives,
        reference_point=request.preference.aspiration_levels,
        num_desired=request.num_desired,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
    )
    # create a new preference in the DB
    preference_db = PreferenceDB(user_id=user.id, problem_id=problem_db.id, preference=request.preference)

    session.add(preference_db)
    session.commit()
    session.refresh(preference_db)

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
        statement = select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find state with id={request.parent_state_id}"
            )

    nimbus_state = NIMBUSClassificationState(
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        current_objectives=request.current_objectives,
        num_desired=request.num_desired,
        previous_preference=request.preference,
    )

    # create DB state and add it to the DB
    state = StateDB(
        problem_id=problem_db.id,
        preference_id=preference_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=nimbus_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    # Collect all current solutions
    current_solutions: list[SolutionAddress] = []
    for i, result in enumerate(solver_results):
        current_solutions.append(
            SolutionAddress(
                objective_values=result.optimal_objectives,
                address_state=state.id,
                address_result=i
            )
        )
    saved_solutions = collect_saved_solutions(user, request.problem_id, session)
    all_solutions = collect_all_solutions(user, request.problem_id, session)
    # all_solutions = collect_all_solutions(state)

    return NIMBUSClassificationResponse(
        state_id=state.id,
        previous_preference=request.preference,
        previous_objectives=request.current_objectives,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions
    )




@router.post("/initialize")
def initialize(
    request: NIMBUSInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSClassificationResponse | NIMBUSInitializationResponse | IntermediateSolutionResponse:
    """Initialize the problem for the NIMBUS method."""
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

    # find the latest NIMBUSClassificationState for the problem and session
    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == problem_db.id,
            StateDB.session_id == (interactive_session.id if interactive_session is not None else None),
            )
        .where(or_(
            # Normal NIMBUS states
            and_(
                StateDB.state["method"] == "nimbus",
                or_(
                    StateDB.state["phase"] == "solve_candidates",
                    StateDB.state["phase"] == "initialize",
                )
            ),
            # Generic states with NIMBUS context
            and_(
                StateDB.state["method"] == "generic",
                StateDB.state["context"] == "nimbus",
                StateDB.state["phase"] == "solve_intermediate"
            )
        ))
        .order_by(StateDB.id.desc())
    )
    state = session.exec(statement).first()

    if state is not None:
        # Collect saved solutions and all solutions that are common for all response types
        saved_solutions = collect_saved_solutions(user, request.problem_id, session)
        all_solutions = collect_all_solutions(user, request.problem_id, session)

        # Check if the state is an intermediate solution state
        if state.state.method == "generic" and state.state.phase == "solve_intermediate":
            intermediate_state: IntermediateSolutionState = state.state
            # Collect current solutions
            current_solutions: list[SolutionAddress] = []
            for i, result in enumerate(intermediate_state.solver_results):
                current_solutions.append(
                    SolutionAddress(
                        objective_values=result.optimal_objectives,
                        address_state=state.id,
                        address_result=i
                    )
                )
            # Return intermediate solution response
            return IntermediateSolutionResponse(
                state_id=state.id,
                reference_solution_1=intermediate_state.reference_solution_1,
                reference_solution_2=intermediate_state.reference_solution_2,
                current_solutions=current_solutions,
                saved_solutions=saved_solutions,
                all_solutions=all_solutions
            )
        # Handle NIMBUS-specific states
        nimbus_state: NIMBUSClassificationState | NIMBUSInitializationState = state.state
        # Collect current solutions for NIMBUS states
        current_solutions: list[SolutionAddress] = []
        for i, result in enumerate(nimbus_state.solver_results):
            current_solutions.append(
                SolutionAddress(
                    objective_values=result.optimal_objectives,
                    address_state=state.id,
                    address_result=i
                )
            )
        # Check if we have a classification state by checking for previous_preference attribute
        if hasattr(nimbus_state, 'previous_preference'):
            return NIMBUSClassificationResponse(
                state_id=state.id,
                previous_preference=nimbus_state.previous_preference,
                previous_objectives=nimbus_state.current_objectives,
                current_solutions=current_solutions,
                saved_solutions=saved_solutions,
                all_solutions=all_solutions
            )

        return NIMBUSInitializationResponse(
            state_id=state.id,
            current_solutions=current_solutions,
            saved_solutions=saved_solutions,
            all_solutions=all_solutions
        )
    # if there is no last nimbus state, generate a starting point and create an initialization state
    start_result = generate_starting_point(
                problem=problem,
                solver=request.solver,
            )
    # fetch parent state if it is given
    if request.parent_state_id is None:
        parent_state = None
    else:
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find state with id={request.parent_state_id}"
            )

    nimbus_state = NIMBUSInitializationState(
        solver=request.solver,
        solver_results=[start_result],
    )

    # create DB state and add it to the DB
    state = StateDB(
        problem_id=problem_db.id,
        preference_id=None,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=nimbus_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    current_solutions: list[SolutionAddress] = []
    for i, result in enumerate(nimbus_state.solver_results):
        current_solutions.append(
            SolutionAddress(
                objective_values=result.optimal_objectives,
                address_state=state.id,
                address_result=i
            )
        )
    # There are no saved solutions, since this is the first state
    saved_solutions = []
    all_solutions = current_solutions.copy()

    return NIMBUSInitializationResponse(
        state_id=state.id,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions
    )

@router.post("/save")
def save(
    request: NIMBUSSaveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSSaveResponse:
    """Save solutions."""
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
        statement = select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find state with id={request.parent_state_id}"
            )

    # Check for duplicate solutions and update names instead of saving duplicates
    updated_solutions = []
    new_solutions = []

    for solution in request.solutions:
        existing_solution = session.exec(
            select(UserSavedSolutionDB).where(
                UserSavedSolutionDB.address_state == solution.address_state,
                UserSavedSolutionDB.address_result == solution.address_result,
            )
        ).first()

        if existing_solution is not None:
            # Update the name of the existing solution
            existing_solution.name = solution.name
            session.add(existing_solution)
            updated_solutions.append(solution.to_solution_address())
        else:
            # This is a new solution
            new_solutions.append(solution)

    # Commit the name updates
    if updated_solutions:
        session.commit()

    # save solver results for state in SolverResults format just for consistency (dont save name field to state)
    save_state = NIMBUSSaveState(
        solution_addresses=[solution.to_solution_address() for solution in request.solutions]
    )

    # create DB state
    state = StateDB(
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
    )
    # Only save new solutions to the user's archive
    if new_solutions:
        user_save_solutions(state, new_solutions, user.id, session)
    else:
        # Still need to add the state to the database
        session.add(state)
        session.commit()
        session.refresh(state)

    return NIMBUSSaveResponse(
        state_id = state.id
    )


@router.post("/intermediate")
def solve_nimbus_intermediate(
    request: IntermediateSolutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> IntermediateSolutionResponse:
    """Solve intermediate solutions by forwarding the request to generic intermediate endpoint with context nimbus."""
    # Add NIMBUS context to request
    request.context = "nimbus"
    # Forward to generic endpoint
    intermediate_state, state_id = solve_intermediate(
        request,
        user,
        session
        )

    current_solutions: list[SolutionAddress] = []
    for i, result in enumerate(intermediate_state.solver_results):
        current_solutions.append(
            SolutionAddress(
                objective_values=result.optimal_objectives,
                address_state=state_id,
                address_result=i
            )
        )
    # Get saved solutions for this user and problem
    saved_solutions = collect_saved_solutions(user, request.problem_id, session)
    # Get all solutions including the newly generated intermediate ones
    all_solutions = collect_all_solutions(user, request.problem_id, session)

    return IntermediateSolutionResponse(
        state_id=state_id,
        reference_solution_1=intermediate_state.reference_solution_1,
        reference_solution_2=intermediate_state.reference_solution_2,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions
    )
