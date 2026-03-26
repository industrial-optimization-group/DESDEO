"""Defines end-points to access functionalities related to the XNIMBUS method (explainable NIMBUS).

XNIMBUS reuses the NIMBUS solving logic but creates states with XNIMBUS-specific
StateKind values so that NIMBUS and XNIMBUS sessions on the same problem don't collide.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from desdeo.api.models import (
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
    ReferencePoint,
    SolutionReference,
    SolutionReferenceResponse,
    StateDB,
    UserSavedSolutionDB,
)
from desdeo.api.models.generic import SolutionInfo
from desdeo.api.models.generic_states import StateKind
from desdeo.api.models.nimbus import NIMBUSMultiplierRequest, NIMBUSMultiplierResponse
from desdeo.api.models.state import IntermediateSolutionState
from desdeo.api.routers.generic import solve_intermediate
from desdeo.api.routers.nimbus import (
    collect_all_solutions,
    collect_saved_solutions,
)
from desdeo.api.routers.nimbus import (
    get_multipliers_info as nimbus_get_multipliers_info,
)
from desdeo.api.routers.problem import check_solver
from desdeo.mcdm.nimbus import generate_starting_point, solve_sub_problems
from desdeo.problem import Problem
from desdeo.tools import SolverResults

from .utils import ContextField, SessionContext, SessionContextGuard

router = APIRouter(prefix="/method/xnimbus")


@router.post("/solve")
def solve_solutions(
    request: NIMBUSClassificationRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> NIMBUSClassificationResponse:
    """Solve the problem using the XNIMBUS method."""
    db_session = context.db_session
    user = context.user
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    solver = check_solver(problem_db=problem_db)
    problem = Problem.from_problemdb(problem_db)

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
        previous_preferences=request.preference,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=nimbus_state,
        kind=StateKind.XNIMBUS_SOLVE,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    current_solutions: list[SolutionReference] = []
    for i, _ in enumerate(solver_results):
        current_solutions.append(SolutionReference(state=state, solution_index=i))

    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)

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
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> NIMBUSInitializationResponse:
    """Initialize the problem for the XNIMBUS method."""
    db_session = context.db_session
    user = context.user
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    solver = check_solver(problem_db=problem_db)
    problem = Problem.from_problemdb(problem_db)

    if isinstance(ref_point := request.starting_point, ReferencePoint):
        starting_point = ref_point.aspiration_levels
    elif isinstance(info := request.starting_point, SolutionInfo):
        statement = select(StateDB).where(StateDB.id == info.state_id)
        state = db_session.exec(statement).first()

        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"StateDB with index {info.state_id} could not be found.",
            )

        starting_point = state.state.result_objective_values[info.solution_index]
    else:
        starting_point = None

    start_result = generate_starting_point(
        problem=problem,
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=solver,
        solver_options=request.solver_options,
    )

    initialization_state = NIMBUSInitializationState(
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_results=start_result,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=initialization_state,
        kind=StateKind.XNIMBUS_INIT,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    current_solutions = [SolutionReference(state=state, solution_index=0)]
    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)

    return NIMBUSInitializationResponse(
        state_id=state.id,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
    )


@router.post("/save")
def save(
    request: NIMBUSSaveRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> NIMBUSSaveResponse:
    """Save solutions."""
    db_session = context.db_session
    user = context.user
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    if request.parent_state_id is None:
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )
    else:
        parent_state = db_session.exec(select(StateDB).where(StateDB.id == request.parent_state_id)).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    updated_solutions: list[UserSavedSolutionDB] = []
    new_solutions: list[UserSavedSolutionDB] = []

    for info in request.solution_info:
        existing_solution = db_session.exec(
            select(UserSavedSolutionDB).where(
                UserSavedSolutionDB.origin_state_id == info.state_id,
                UserSavedSolutionDB.solution_index == info.solution_index,
            )
        ).first()

        if existing_solution is not None:
            existing_solution.name = info.name
            db_session.add(existing_solution)
            updated_solutions.append(existing_solution)
        else:
            new_solution = UserSavedSolutionDB.from_state_info(
                db_session, user.id, request.problem_id, info.state_id, info.solution_index, info.name
            )
            db_session.add(new_solution)
            new_solutions.append(new_solution)

    if updated_solutions or new_solutions:
        db_session.commit()
        [db_session.refresh(row) for row in updated_solutions + new_solutions]

    save_state = NIMBUSSaveState(solutions=updated_solutions + new_solutions)

    state = StateDB.create(
        database_session=db_session,
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
        kind=StateKind.XNIMBUS_SAVE,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return NIMBUSSaveResponse(state_id=state.id)


@router.post("/intermediate")
def solve_xnimbus_intermediate(
    request: IntermediateSolutionRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> NIMBUSIntermediateSolutionResponse:
    """Solve intermediate solutions with xnimbus context."""
    db_session = context.db_session
    user = context.user

    request.context = "xnimbus"
    intermediate_response = solve_intermediate(request, context)

    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)

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
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> (
    NIMBUSInitializationResponse
    | NIMBUSClassificationResponse
    | NIMBUSIntermediateSolutionResponse
    | NIMBUSFinalizeResponse
):
    """Get the latest XNIMBUS state if it exists, or initialize a new one if it doesn't."""
    db_session = context.db_session
    user = context.user
    interactive_session = context.interactive_session

    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == request.problem_id,
            StateDB.session_id == (interactive_session.id if interactive_session else user.active_session_id),
        )
        .order_by(StateDB.id.desc())
    )
    states = db_session.exec(statement).all()

    # Find the latest relevant XNIMBUS state (check base_state.kind)
    latest_state = None
    for state in states:
        if state.base_state is not None and state.base_state.kind in (
            StateKind.XNIMBUS_SOLVE,
            StateKind.XNIMBUS_INIT,
            StateKind.XNIMBUS_FINAL,
            StateKind.XNIMBUS_SAVE,
        ):
            latest_state = state
            break

    if latest_state is not None:
        saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
        all_solutions = collect_all_solutions(user, request.problem_id, db_session)

        solver_results = latest_state.state.solver_results
        current_solutions = (
            [SolutionReference(state=latest_state, solution_index=i) for i in range(len(solver_results))]
            if isinstance(solver_results, list)
            else [SolutionReference(state=latest_state, solution_index=0)]
        )

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
    return initialize(request, context)


@router.post("/finalize")
def finalize_xnimbus(
    request: NIMBUSFinalizeRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> NIMBUSFinalizeResponse:
    """Finalize the XNIMBUS process."""
    db_session = context.db_session
    user = context.user
    interactive_session = context.interactive_session
    parent_state = context.parent_state
    problem_db = context.problem_db

    solution_state_id = request.solution_info.state_id
    solution_index = request.solution_info.solution_index

    state = db_session.exec(select(StateDB).where(StateDB.id == solution_state_id)).first()
    actual_state = state.state if state else None
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

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=final_state,
        kind=StateKind.XNIMBUS_FINAL,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    solution_reference_response = SolutionReferenceResponse(
        solution_index=solution_index,
        state_id=solution_state_id,
        objective_values=final_state.solver_results.optimal_objectives,
        variable_values=final_state.solver_results.optimal_variables,
    )

    return NIMBUSFinalizeResponse(
        state_id=state.id,
        final_solution=solution_reference_response,
        saved_solutions=collect_saved_solutions(user=user, problem_id=problem_db.id, session=db_session),
        all_solutions=collect_all_solutions(user=user, problem_id=problem_db.id, session=db_session),
    )


@router.post("/delete_save")
def delete_save(
    request: NIMBUSDeleteSaveRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> NIMBUSDeleteSaveResponse:
    """Delete a saved solution."""
    db_session = context.db_session

    to_be_deleted = db_session.exec(
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

    db_session.delete(to_be_deleted)
    db_session.commit()

    to_be_deleted = db_session.exec(
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
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> NIMBUSMultiplierResponse:
    """Get Lagrange multipliers info — delegates to the NIMBUS router implementation."""
    return nimbus_get_multipliers_info(request, context)
