"""Defines end-points to access functionalities related to the NIMBUS method."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from numpy import allclose
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    InteractiveSessionDB,
    IntermediateSolutionRequest,
    NIMBUSClassificationRequest,
    NIMBUSClassificationResponse,
    NIMBUSClassificationState,
    NIMBUSDeleteSaveRequest,
    NIMBUSDeleteSaveResponse,
    NIMBUSFinalizeRequest,
    NIMBUSFinalizeResponse,
    NIMBUSFinalState,
    NIMBUSInitializationRequest,
    NIMBUSInitializationResponse,
    NIMBUSInitializationState,
    NIMBUSIntermediateSolutionResponse,
    NIMBUSSaveRequest,
    NIMBUSSaveResponse,
    NIMBUSSaveState,
    ProblemDB,
    ReferencePoint,
    SavedSolutionReference,
    SolutionReference,
    SolutionReferenceResponse,
    StateDB,
    User,
    UserSavedSolutionDB,
)
from desdeo.api.models.generic import SolutionInfo
from desdeo.api.models.state import IntermediateSolutionState
from desdeo.api.routers.generic import solve_intermediate
from desdeo.api.routers.problem import check_solver
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.nimbus import generate_starting_point, solve_sub_problems
from desdeo.problem import Problem
from desdeo.tools import SolverResults

router = APIRouter(prefix="/method/nimbus")


# helper for collecting solutions
def filter_duplicates(solutions: list[SavedSolutionReference]) -> list[SavedSolutionReference]:
    """Filters out the duplicate values of objectives."""
    # No solutions or only one solution. There can not be any duplicates.
    if len(solutions) < 2:
        return solutions

    # Get the objective values
    objective_values_list = [sol.objective_values for sol in solutions]
    # Get the function symbols
    objective_keys = list(objective_values_list[0])
    # Get the corresponding values for functions into a list of lists of values
    valuelists = [[dictionary[key] for key in objective_keys] for dictionary in objective_values_list]
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
def collect_saved_solutions(user: User, problem_id: int, session: Session) -> list[SavedSolutionReference]:
    """Collects all saved solutions for the user and problem."""
    user_saved_solutions = session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.problem_id == problem_id, UserSavedSolutionDB.user_id == user.id
        )
    ).all()

    saved_solutions = [SavedSolutionReference(saved_solution=saved_solution) for saved_solution in user_saved_solutions]

    return filter_duplicates(saved_solutions)


# for collecting solutions for responses in iterate and initialize endpoints
def collect_all_solutions(user: User, problem_id: int, session: Session) -> list[SolutionReference]:
    """Collects all solutions for the user and problem."""
    statement = (
        select(StateDB)
        .where(StateDB.problem_id == problem_id, StateDB.session_id == user.active_session_id)
        .order_by(StateDB.id.desc())
    )
    states = session.exec(statement).all()
    all_solutions = []
    for state in states:
        for i in range(state.state.num_solutions):
            all_solutions.append(SolutionReference(state=state, solution_index=i))

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

    solver = check_solver(problem_db=problem_db)

    problem = Problem.from_problemdb(problem_db)

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

    solver_results: list[SolverResults] = solve_sub_problems(
        problem=problem,
        current_objectives=request.current_objectives,
        reference_point=request.preference.aspiration_levels,
        num_desired=request.num_desired,
        scalarization_options=request.scalarization_options,
        solver=solver,
        solver_options=request.solver_options,
    )

    nimbus_state = NIMBUSClassificationState(
        preferences=request.preference,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        current_objectives=request.current_objectives,
        num_desired=request.num_desired,
        previous_preferences=request.preference,  # why?
    )

    # create DB state and add it to the DB
    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=nimbus_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    # Collect all current solutions
    current_solutions: list[SolutionReference] = []
    for i, _ in enumerate(solver_results):
        current_solutions.append(SolutionReference(state=state, solution_index=i))

    saved_solutions = collect_saved_solutions(user, request.problem_id, session)
    all_solutions = collect_all_solutions(user, request.problem_id, session)

    return NIMBUSClassificationResponse(
        state_id=state.id,
        previous_preference=request.preference,
        previous_objectives=request.current_objectives,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
    )


@router.post("/initialize")
def initialize(
    request: NIMBUSInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSInitializationResponse:
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

    print(interactive_session)

    # fetch the problem from the DB
    statement = select(ProblemDB).where(ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id)
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem with id={request.problem_id} could not be found."
        )

    solver = check_solver(problem_db=problem_db)

    problem = Problem.from_problemdb(problem_db)

    if isinstance(ref_point := request.starting_point, ReferencePoint):
        # ReferencePoint
        starting_point = ref_point.aspiration_levels

    elif isinstance(info := request.starting_point, SolutionInfo):
        # SolutionInfo
        # fetch the solution
        statement = select(StateDB).where(StateDB.id == info.state_id)
        state = session.exec(statement).first()

        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"StateDB with index {info.state_id} could not be found."
            )

        starting_point = state.state.result_objective_values[info.solution_index]

    else:
        # if not starting point is provided, generate it
        starting_point = None

    start_result = generate_starting_point(
        problem=problem,
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=solver,
        solver_options=request.solver_options,
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

    initialization_state = NIMBUSInitializationState(
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_results=start_result,
    )

    # create DB state and add it to the DB
    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=initialization_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    current_solutions = [SolutionReference(state=state, solution_index=0)]
    saved_solutions = collect_saved_solutions(user, request.problem_id, session)
    all_solutions = collect_all_solutions(user, request.problem_id, session)

    return NIMBUSInitializationResponse(
        state_id=state.id,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
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
    updated_solutions: list[UserSavedSolutionDB] = []
    new_solutions: list[UserSavedSolutionDB] = []

    for info in request.solution_info:
        existing_solution = session.exec(
            select(UserSavedSolutionDB).where(
                UserSavedSolutionDB.origin_state_id == info.state_id,
                UserSavedSolutionDB.solution_index == info.solution_index,
            )
        ).first()

        if existing_solution is not None:
            # Update the name of the existing solution
            existing_solution.name = info.name

            session.add(existing_solution)

            updated_solutions.append(existing_solution)
        else:
            # This is a new solution
            new_solution = UserSavedSolutionDB.from_state_info(
                session, user.id, request.problem_id, info.state_id, info.solution_index, info.name
            )

            session.add(new_solution)

            new_solutions.append(new_solution)

    # Commit existing and new solutions
    if updated_solutions or new_solution:
        session.commit()
        [session.refresh(row) for row in updated_solutions + new_solutions]

    # save solver results for state in SolverResults format just for consistency (dont save name field to state)
    save_state = NIMBUSSaveState(solutions=updated_solutions + new_solutions)

    # create DB state
    state = StateDB.create(
        database_session=session,
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return NIMBUSSaveResponse(state_id=state.id)


@router.post("/intermediate")
def solve_nimbus_intermediate(
    request: IntermediateSolutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSIntermediateSolutionResponse:
    """Solve intermediate solutions by forwarding the request to generic intermediate endpoint with context nimbus."""
    # Add NIMBUS context to request
    request.context = "nimbus"
    # Forward to generic endpoint
    intermediate_response = solve_intermediate(request, user, session)

    # Get saved solutions for this user and problem
    saved_solutions = collect_saved_solutions(user, request.problem_id, session)

    # Get all solutions including the newly generated intermediate ones
    all_solutions = collect_all_solutions(user, request.problem_id, session)

    return NIMBUSIntermediateSolutionResponse(
        state_id=intermediate_response.state_id,
        reference_solution_1=intermediate_response.reference_solution_1.objective_values,
        reference_solution_2=intermediate_response.reference_solution_2.objective_values,
        current_solutions=intermediate_response.intermediate_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
    )


@router.post("/get-or-initialize")
def get_or_initialize(
    request: NIMBUSInitializationRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSInitializationResponse | NIMBUSClassificationResponse | NIMBUSIntermediateSolutionResponse:
    """Get the latest NIMBUS state if it exists, or initialize a new one if it doesn't."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == request.session_id)
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # use active session instead
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == user.active_session_id)
        interactive_session = session.exec(statement).first()

    # Look for latest relevant state in the session
    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == request.problem_id,
            StateDB.session_id == (interactive_session.id if interactive_session else user.active_session_id),
        )
        .order_by(StateDB.id.desc())
    )
    states = session.exec(statement).all()

    # Find the latest relevant state (NIMBUS classification, initialization, or intermediate with NIMBUS context)
    latest_state = None
    for state in states:
        if isinstance(state.state, (NIMBUSClassificationState | NIMBUSInitializationState | NIMBUSFinalState)) or (
            isinstance(state.state, IntermediateSolutionState) and state.state.context == "nimbus"
        ):
            latest_state = state
            break

    if latest_state is not None:
        saved_solutions = collect_saved_solutions(user, request.problem_id, session)
        all_solutions = collect_all_solutions(user, request.problem_id, session)
        # Handle both single result and list of results cases
        solver_results = latest_state.state.solver_results
        if isinstance(solver_results, list):
            current_solutions = [
                SolutionReference(state=latest_state, solution_index=i) for i in range(len(solver_results))
            ]
        else:
            # Single result case (NIMBUSInitializationState)
            current_solutions = [SolutionReference(state=latest_state, solution_index=0)]

        if isinstance(latest_state.state, NIMBUSClassificationState):
            return NIMBUSClassificationResponse(
                state_id=latest_state.id,
                previous_preference=latest_state.state.preferences,
                previous_objectives=latest_state.state.current_objectives,
                current_solutions=current_solutions,
                saved_solutions=saved_solutions,
                all_solutions=all_solutions,
            )

        if isinstance(latest_state.state, IntermediateSolutionState):
            return NIMBUSIntermediateSolutionResponse(
                state_id=latest_state.id,
                reference_solution_1=latest_state.state.reference_solution_1,
                reference_solution_2=latest_state.state.reference_solution_2,
                current_solutions=current_solutions,
                saved_solutions=saved_solutions,
                all_solutions=all_solutions,
            )

        # NIMBUSInitializationState
        return NIMBUSInitializationResponse(
            state_id=latest_state.id,
            current_solutions=current_solutions,
            saved_solutions=saved_solutions,
            all_solutions=all_solutions,
        )

    # No relevant state found, initialize a new one
    return initialize(request, user, session)


@router.post("/finalize")
def finalize_nimbus(
    request: NIMBUSFinalizeRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> NIMBUSFinalizeResponse:
    """An endpoint for finishing up the nimbus process.

    Args:
        request (NIMBUSFinalizeRequest): The request containing the final solution, etc.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): The database session.

    Raises:
        HTTPException

    Returns:
        NIMBUSFinalizeResponse: Response containing state id of the final solution.
    """
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

    if request.parent_state_id is None:
        parent_state = None
    else:
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find state with id={request.parent_state_id}"
            )

    # fetch the problem from the DB
    statement = select(ProblemDB).where(ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id)
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem with id={request.problem_id} could not be found."
        )

    solution_state_id = request.solution_info.state_id
    solution_index = request.solution_info.solution_index

    statement = select(StateDB).where(StateDB.id == solution_state_id)
    actual_state = session.exec(statement).first().state
    if actual_state is None:
        raise HTTPException(
            detail="No concrete substate!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    final_state = NIMBUSFinalState(
        solver_results  = actual_state.solver_results[solution_index],
        reference_point = request.preferences.aspiration_levels,
    )

    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=final_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return NIMBUSFinalizeResponse(
        state_id=state.id,
        final_solution=SolutionReferenceResponse(
            name=None,
            solution_index=solution_index,
            state_id=solution_state_id,
            objective_values=actual_state.solver_results[solution_index].optimal_objectives,
            variable_values=actual_state.solver_results[solution_index].optimal_variables,
        )
    )

@router.post("/delete_save")
def delete_save(
    request: NIMBUSDeleteSaveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> NIMBUSDeleteSaveResponse:
    """Endpoint for deleting saved solutions.

    Args:
        request (NIMBUSDeleteSaveRequest): request containing necessary information for deleting a save
        user (Annotated[User, Depends): the current  (logged in) user
        session (Annotated[Session, Depends): database session

    Raises:
        HTTPException

    Returns:
        NIMBUSDeleteSaveResponse: Response acknowledging the deletion of save and other useful info.
    """
    to_be_deleted = session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.origin_state_id == request.state_id,
            UserSavedSolutionDB.solution_index == request.solution_index,
        )
    ).first()

    if to_be_deleted is None:
        raise HTTPException(
            detail="Unable to find a saved solution!",
            status_code=status.HTTP_404_NOT_FOUND
        )

    session.delete(to_be_deleted)
    session.commit()

    to_be_deleted = session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.origin_state_id == request.state_id,
            UserSavedSolutionDB.solution_index == request.solution_index,
        )
    ).first()

    if to_be_deleted is not None:
        raise HTTPException(
            detail="Could not delete the saved solution!",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return NIMBUSDeleteSaveResponse(
        message="Save deleted."
    )
