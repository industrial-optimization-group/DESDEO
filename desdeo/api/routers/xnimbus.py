"""Defines end-points to access functionalities related to the XNIMBUS method (explainable NIMBUS)."""

from collections import defaultdict
import re
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
from desdeo.api.models.generic_states import StateKind
from desdeo.api.models.nimbus import NIMBUSMultiplierRequest, NIMBUSMultiplierResponse
from desdeo.api.models.state import IntermediateSolutionState
from desdeo.api.routers.generic import solve_intermediate
from desdeo.api.routers.problem import check_solver
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.nimbus import generate_starting_point, solve_sub_problems
from desdeo.problem import Problem
from desdeo.tools import SolverResults

router = APIRouter(prefix="/method/xnimbus")


# helper for collecting solutions
def filter_duplicates(
    solutions: list[SavedSolutionReference],
) -> list[SavedSolutionReference]:
    """Filters out the duplicate values of objectives."""
    # No solutions or only one solution. There can not be any duplicates.
    if len(solutions) < 2:
        return solutions

    # Get the objective values
    objective_values_list = [sol.objective_values for sol in solutions]
    # Get the function symbols
    objective_keys = list(objective_values_list[0])
    # Get the corresponding values for functions into a list of lists of values
    valuelists = [
        [dictionary[key] for key in objective_keys]
        for dictionary in objective_values_list
    ]
    # Check duplicate indices
    duplicate_indices = []
    for i in range(len(solutions) - 1):
        for j in range(i + 1, len(solutions)):
            # If all values of the objective functions are (nearly) identical, that's a duplicate
            if allclose(
                valuelists[i], valuelists[j]
            ):  # TODO: "similarity tolerance" from problem metadata
                duplicate_indices.append(i)

    # Quite the memory hell. See If there's a smarter way to do this
    new_solutions = []
    for i in range(len(solutions)):
        if i not in duplicate_indices:
            new_solutions.append(solutions[i])

    return new_solutions


# for collecting solutions for responses in iterate and initialize endpoints
def collect_saved_solutions(
    user: User, problem_id: int, session: Session
) -> list[SavedSolutionReference]:
    """Collects all saved solutions for the user and problem."""
    user_saved_solutions = session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.problem_id == problem_id,
            UserSavedSolutionDB.user_id == user.id,
        )
    ).all()

    saved_solutions = [
        SavedSolutionReference(saved_solution=saved_solution)
        for saved_solution in user_saved_solutions
    ]

    return filter_duplicates(saved_solutions)


# for collecting solutions for responses in iterate and initialize endpoints
def collect_all_solutions(
    user: User, problem_id: int, session: Session
) -> list[SolutionReference]:
    """Collects all solutions for the user and problem."""
    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == problem_id,
            StateDB.session_id == user.active_session_id,
        )
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
    """Solve the problem using the XNIMBUS method."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )

        interactive_session = session.exec(statement).first()

    # fetch the problem from the DB
    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id
    )
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
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

    # create DB state and add it to the DB with explicit XNIMBUS kind
    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=nimbus_state,
        kind=StateKind.XNIMBUS_SOLVE,
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
    """Initialize the problem for the XNIMBUS method."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )

        interactive_session = session.exec(statement).first()

    print(interactive_session)

    # fetch the problem from the DB
    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id
    )
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"StateDB with index {info.state_id} could not be found.",
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    initialization_state = NIMBUSInitializationState(
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_results=start_result,
    )

    # create DB state and add it to the DB with explicit XNIMBUS kind
    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=initialization_state,
        kind=StateKind.XNIMBUS_INIT,
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
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
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
                session,
                user.id,
                request.problem_id,
                info.state_id,
                info.solution_index,
                info.name,
            )

            session.add(new_solution)

            new_solutions.append(new_solution)

    # Commit existing and new solutions
    if updated_solutions or new_solution:
        session.commit()
        [session.refresh(row) for row in updated_solutions + new_solutions]

    # save solver results for state in SolverResults format just for consistency (dont save name field to state)
    save_state = NIMBUSSaveState(solutions=updated_solutions + new_solutions)

    # create DB state with explicit XNIMBUS kind
    state = StateDB.create(
        database_session=session,
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
        kind=StateKind.XNIMBUS_SAVE,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return NIMBUSSaveResponse(state_id=state.id)


@router.post("/intermediate")
def solve_xnimbus_intermediate(
    request: IntermediateSolutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSIntermediateSolutionResponse:
    """Solve intermediate solutions by forwarding the request to generic intermediate endpoint with context xnimbus."""
    # Add XNIMBUS context to request
    request.context = "xnimbus"
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
) -> (
    NIMBUSInitializationResponse
    | NIMBUSClassificationResponse
    | NIMBUSIntermediateSolutionResponse
    | NIMBUSFinalizeResponse
):
    """Get the latest XNIMBUS state if it exists, or initialize a new one if it doesn't."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )
        interactive_session = session.exec(statement).first()

    # Look for latest relevant state in the session
    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == request.problem_id,
            StateDB.session_id
            == (
                interactive_session.id
                if interactive_session
                else user.active_session_id
            ),
        )
        .order_by(StateDB.id.desc())
    )
    states = session.exec(statement).all()

    # Find the latest relevant XNIMBUS state
    latest_state = None
    for state in states:
        if isinstance(
            state.state,
            (NIMBUSClassificationState | NIMBUSInitializationState | NIMBUSFinalState),
        ) or (
            isinstance(state.state, IntermediateSolutionState)
            and state.state.context == "xnimbus"
        ):
            # Check that it's an XNIMBUS state by looking at the base state kind
            if state.base_state.kind in [
                StateKind.XNIMBUS_SOLVE,
                StateKind.XNIMBUS_INIT,
                StateKind.XNIMBUS_FINAL,
                StateKind.XNIMBUS_SAVE,
            ]:
                latest_state = state
                break

    if latest_state is not None:
        saved_solutions = collect_saved_solutions(user, request.problem_id, session)
        all_solutions = collect_all_solutions(user, request.problem_id, session)
        # Handle both single result and list of results cases
        solver_results = latest_state.state.solver_results
        if isinstance(solver_results, list):
            current_solutions = [
                SolutionReference(state=latest_state, solution_index=i)
                for i in range(len(solver_results))
            ]
        else:
            # Single result case (NIMBUSInitializationState)
            current_solutions = [
                SolutionReference(state=latest_state, solution_index=0)
            ]

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

        if isinstance(latest_state.state, NIMBUSFinalState):

            solution_index = latest_state.state.solution_result_index
            origin_state_id = latest_state.state.solution_origin_state_id

            final_solution_ref_res = SolutionReferenceResponse(
                solution_index=solution_index,
                state_id=origin_state_id,
                objective_values=latest_state.state.solver_results.optimal_objectives,
                variable_values=latest_state.state.solver_results.optimal_variables,
            )

            return NIMBUSFinalizeResponse(
                state_id=latest_state.id,
                final_solution=final_solution_ref_res,
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
def finalize_xnimbus(
    request: NIMBUSFinalizeRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSFinalizeResponse:
    """An endpoint for finishing up the xnimbus process.

    Args:
        request (NIMBUSFinalizeRequest): The request containing the final solution, etc.
        user (Annotated[User, Depends): The current user.
        session (Annotated[Session, Depends): The database session.

    Raises:
        HTTPException

    Returns:
        NIMBUSFinalizeResponse: Response containing info on the final solution.
    """
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )

        interactive_session = session.exec(statement).first()

    if request.parent_state_id is None:
        parent_state = None
    else:
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    # fetch the problem from the DB
    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id
    )
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
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
        solution_origin_state_id=solution_state_id,
        solution_result_index=solution_index,
        solver_results=actual_state.solver_results[solution_index],
    )

    # create DB state with explicit XNIMBUS kind
    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=final_state,
        kind=StateKind.XNIMBUS_FINAL,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    solution_reference_response = SolutionReferenceResponse(
        solution_index=solution_index,
        state_id=solution_state_id,
        objective_values=final_state.solver_results.optimal_objectives,
        variable_values=final_state.solver_results.optimal_variables,
    )

    return NIMBUSFinalizeResponse(
        state_id=state.id,
        final_solution=solution_reference_response,
        saved_solutions=collect_saved_solutions(
            user=user, problem_id=problem_db.id, session=session
        ),
        all_solutions=collect_all_solutions(
            user=user, problem_id=problem_db.id, session=session
        ),
    )


@router.post("/delete_save")
def delete_save(
    request: NIMBUSDeleteSaveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
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
            status_code=status.HTTP_404_NOT_FOUND,
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return NIMBUSDeleteSaveResponse(message="Save deleted.")


@router.post("/get-multipliers-info")
def get_multipliers_info(
    request: NIMBUSMultiplierRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NIMBUSMultiplierResponse:
    """Get Lagrange multipliers information from an state. The multipliers are available from the solver results."""
    empty_response = {"lagrange_multipliers": None}
    state = session.exec(select(StateDB).where(StateDB.id == request.state_id)).first()

    if state is None or not hasattr(state, "state"):
        return empty_response

    actual_state = state.state

    # Check if the request has the objective symbols, if not, we will try to extract them from the solver results if possible. If not, we will use the default f_{index} format for filtering the multipliers.
    objective_symbols = request.objective_symbols

    if (
        not hasattr(actual_state, "solver_results")
        or actual_state.solver_results is None
    ):
        return empty_response

    lagrange_multipliers = []
    constraint_values = []

    # Handle states with multiple results (list of SolverResults)
    if isinstance(actual_state.solver_results, list):
        for result in actual_state.solver_results:
            if (
                hasattr(result, "lagrange_multipliers")
                and result.lagrange_multipliers is not None
            ):
                lagrange_multipliers.append(
                    filter_lagrange_multipliers(
                        result.lagrange_multipliers, objective_symbols
                    )
                )
                constraint_values.append(
                    filter_constraint_values(
                        result.constraint_values, objective_symbols
                    )
                )

                print("Added multipliers:", result.lagrange_multipliers)
            else:
                lagrange_multipliers.append(None)
                constraint_values.append(None)

    # Handle states with single result (single SolverResults object)
    else:
        result = actual_state.solver_results
        if (
            hasattr(result, "lagrange_multipliers")
            and result.lagrange_multipliers is not None
        ):
            if (
                hasattr(result, "constraint_values")
                and result.constraint_values is not None
            ):
                print("Constraint values:", result.constraint_values)

            lagrange_multipliers.append(
                filter_lagrange_multipliers(
                    result.lagrange_multipliers, objective_symbols
                )
            )
            constraint_values.append(
                filter_constraint_values(result.constraint_values, objective_symbols)
            )
        else:
            lagrange_multipliers.append(None)
            constraint_values.append(None)

    # Compute tradeoffs matrix for each solution
    tradeoffs_list = []
    for filtered_mults in lagrange_multipliers:
        tradeoff = compute_tradeoffs(filtered_mults)
        tradeoffs_list.append(tradeoff)

    if (
        isinstance(actual_state, NIMBUSClassificationState)
        and state.base_state is not None
        and state.base_state.kind == StateKind.XNIMBUS_SOLVE
    ):
        # Save filtered multipliers and tradeoffs
        actual_state.filtered_lagrange_multipliers = lagrange_multipliers
        actual_state.tradeoffs_matrix = tradeoffs_list
        session.add(actual_state)
        session.commit()

    print(lagrange_multipliers)

    print("Constraint values:", constraint_values)

    # Determine the active objectives based on the constraint values (if available). Active objectives are those for which the corresponding constraint is active (constraint value is close to zero).
    active_objectives = []
    if constraint_values and objective_symbols:
        for constraint_dict in constraint_values:
            active_objs_for_result = []
            for obj, value in constraint_dict.items():
                if (
                    obj in objective_symbols and value >= 0
                ):  # If its lower than zero, the constraint is not active, if its close to zero, it is active (we can use a tolerance here if needed). Not sure if works for minimization problems, need to check.
                    active_objs_for_result.append(obj)
            active_objectives.append(active_objs_for_result)
    elif objective_symbols:
        # If constraint values are not available, we can determine if they are active based on the magnitude of the multiplier using a threshold (e.g., if the multiplier is close to zero, we can consider the objective as inactive). This is a very rough approximation and should be used with caution.
        threshold = 1e-5  # This threshold can be adjusted based on the problem characteristics and solver precision.
        for multiplier_dict in lagrange_multipliers:
            active_objs_for_result = []
            for obj in objective_symbols:
                multiplier_value = multiplier_dict.get(obj, 0.0)
                if abs(multiplier_value) > threshold:
                    active_objs_for_result.append(obj)
            active_objectives.append(active_objs_for_result)
    else:
        # If no objective symbols and no constraint values are available, we will assume that all objectives with non-zero multipliers are active and we will use the default f_{index} format for the objective names.
        threshold = 1e-5
        for multiplier_dict in lagrange_multipliers:
            active_objs_for_result = []
            for obj, multiplier_value in multiplier_dict.items():
                if abs(multiplier_value) > threshold:
                    active_objs_for_result.append(obj)
            active_objectives.append(active_objs_for_result)

    print("Active objectives:", active_objectives)

    return {
        "lagrange_multipliers": lagrange_multipliers,
        "tradeoffs_matrix": tradeoffs_list,
        "active_objectives": active_objectives,
    }


def compute_tradeoffs(
    filtered_multipliers: dict[str, float] | None,
) -> dict[str, dict[str, float]] | None:
    """Compute tradeoffs matrix from filtered Lagrange multipliers.

    Tradeoffs represent marginal rates of substitution between objectives.
    For objectives i and j, tradeoff[i][j] = -lambda_j / lambda_i
    """
    if not filtered_multipliers:
        return None

    # Get objective keys (e.g., "f_0", "f_1" or actual symbols)
    objectives = list(filtered_multipliers.keys())

    # Initialize tradeoffs matrix
    tradeoffs = {}

    for obj_i in objectives:
        tradeoffs[obj_i] = {}
        lambda_i = filtered_multipliers[obj_i]

        # Avoid division by zero
        if lambda_i == 0:
            for obj_j in objectives:
                tradeoffs[obj_i][obj_j] = 0.0 if obj_i != obj_j else 1.0
            continue

        for obj_j in objectives:
            if obj_i == obj_j:
                # Diagonal elements are 1
                tradeoffs[obj_i][obj_j] = 1.0
            else:
                lambda_j = filtered_multipliers[obj_j]
                # Tradeoff: -lambda_j / lambda_i
                tradeoffs[obj_i][obj_j] = -lambda_j / lambda_i

    return tradeoffs


def filter_lagrange_multipliers(
    lagrange_multipliers, objective_symbols=None
) -> dict[str, float]:
    # return [x.lagrange_multipliers for x in self.solver_results]
    result = []

    # filter multipliers to keep only one per objective. If the symbols are available, use them to select the multiplier. If not, use f_{index} format.
    grouped = defaultdict(list)

    for key, value in lagrange_multipliers.items():
        if objective_symbols is None:
            match = re.search(
                r"f_(\d+)", key
            )  # Match keys like "f_0", "f_1", etc. and extract the objective number
            if match:
                f_i = match.group(1)  # Extract the objective number
                grouped[f_i].append((key, value))
        else:  # Get one multiplier per objective based on the symbols in the problem definition
            for symbol in objective_symbols:
                if symbol in key:
                    grouped[symbol].append((key, value))
                    break

    # Select preferred multiplier for each objective.
    filtered_multipliers = {}
    for obj_num, entries in grouped.items():
        # Prefer non-"eq" constraints
        preferred = next(
            (entry for entry in entries if not entry[0].endswith("eq")), None
        )
        if preferred is None and entries:
            preferred = entries[0]

        if preferred:
            # use the symbol as key if available, otherwise use f_{index} format
            key = preferred[0]
            if objective_symbols is not None and obj_num in objective_symbols:
                key = obj_num
            filtered_multipliers[key] = preferred[1]

    # result.append(filtered_multipliers)
    # Check if there are multiplier for each objective, if not, assignt that value to 0 (this can happen if the solver does not return multipliers for inactive constraints)
    if objective_symbols is not None:
        for symbol in objective_symbols:
            if symbol not in filtered_multipliers:
                filtered_multipliers[symbol] = 0.0
    else:
        # If symbols are not available, we will assume that the objectives are numbered from 0 to n-1 and use f_{index} format for keys
        max_index = -1
        for key in filtered_multipliers.keys():
            match = re.search(r"f_(\d+)", key)
            if match:
                index = int(match.group(1))
                max_index = max(max_index, index)

        for i in range(max_index + 1):
            key = f"f_{i}"
            if key not in filtered_multipliers:
                filtered_multipliers[key] = 0.0

    return filtered_multipliers


def filter_constraint_values(
    constraint_values, objective_symbols=None
) -> dict[str, float]:
    # Similar to filter_lagrange_multipliers but for constraint values. We will keep only one value per constraint and we will use the same grouping and selection logic as for the multipliers.
    grouped = defaultdict(list)

    for key, value in constraint_values.items():
        if objective_symbols is None:
            match = re.search(
                r"f_(\d+)", key
            )  # Match keys like "f_0", "f_1", etc. and extract the objective number
            if match:
                f_i = match.group(1)  # Extract the objective number
                grouped[f_i].append((key, value))
        else:  # Get one value per constraint based on the symbols in the problem definition
            for symbol in objective_symbols:
                if symbol in key:
                    grouped[symbol].append((key, value))
                    break

    filtered_values = {}
    for obj_num, entries in grouped.items():
        preferred = next(
            (entry for entry in entries if not entry[0].endswith("eq")), None
        )
        if preferred is None and entries:
            preferred = entries[0]

        if preferred:
            key = preferred[0]
            if objective_symbols is not None and obj_num in objective_symbols:
                key = obj_num
            filtered_values[key] = preferred[1]

    return filtered_values
