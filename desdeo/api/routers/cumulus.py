"""Defines end-points to access functionalities related to the CUMULUS method."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import engine, get_session
from desdeo.api.models import (
    CumulusFinalState,
    CumulusInitializationState,
    CumulusModificationState,
    CumulusObjectiveConstraintState,
    CumulusSaveState,
    IntermediateSolutionRequest,
    IntermediateSolutionState,
    ReferencePoint,
    StateDB,
    User,
    UserSavedSolutionDB,
)
from desdeo.api.models.cumulus import (
    CumulusClassificationRequest,
    CumulusClassificationResponse,
    CumulusDeleteSaveRequest,
    CumulusDeleteSaveResponse,
    CumulusFinalizeRequest,
    CumulusFinalizeResponse,
    CumulusInitializationRequest,
    CumulusInitializationResponse,
    CumulusIntermediateSolutionResponse,
    CumulusModificationRequest,
    CumulusModificationResponse,
    CumulusObjectiveConstraintRequest,
    CumulusObjectiveConstraintResponse,
    CumulusSaveRequest,
    CumulusSaveResponse,
    CumulusScenarioSetupResponse,
    ProblemModification,
)
from desdeo.api.models.generic import SolutionInfo
from desdeo.api.models.generic_states import SolutionReference, SolutionReferenceResponse, StateKind
from desdeo.api.models.problem import ConstraintDB, ProblemDB
from desdeo.api.models.scenario import ScenarioModelDB
from desdeo.api.models.state import CumulusClassificationState
from desdeo.api.routers.problem import check_solver
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.cumulus import CumulusScalarization, generate_starting_point, solve_sub_problems
from desdeo.mcdm.reference_point_method import rpm_intermediate_solutions
from desdeo.problem import Problem, ScenarioModel
from desdeo.problem.schema import Constraint
from desdeo.tools import SolverResults, guess_best_solver
from desdeo.tools.utils import payoff_table_method

from .utils import (
    ContextField,
    SessionContext,
    SessionContextGuard,
    apply_problem_modifications,
    collect_all_solutions,
    collect_saved_solutions,
    copy_problem_metadata,
    iter_states_of_kinds,
)

router = APIRouter(prefix="/method/cumulus")


def _get_scenario_model_id(
    problem_id: int,
    session_id: int | None,
    db_session: Session,
) -> int | None:
    """Return the scenario_model_id from the most recent CUMULUS init or solve state that has one."""
    for state in iter_states_of_kinds(
        problem_id, session_id, db_session, (StateKind.CUMULUS_INIT, StateKind.CUMULUS_SOLVE)
    ):
        sm_id = getattr(state, "scenario_model_id", None)
        if sm_id is not None:
            return sm_id
    return None


def _load_scenario_model(
    scenario_model_id: int,
    db_session: Session,
) -> ScenarioModel | None:
    """Load a :class:`ScenarioModel` from the DB given its id."""
    sm_db = db_session.get(ScenarioModelDB, scenario_model_id)
    if sm_db is None or sm_db.base_problem is None:
        return None
    return sm_db.to_scenario_model(base_problem=Problem.from_problemdb(sm_db.base_problem))


def _get_objective_constraint_ids(
    problem_id: int,
    session_id: int | None,
    db_session: Session,
) -> tuple[list[int], list[int]]:
    """Return (hard_constraint_ids, soft_constraint_ids) from the latest objective-constraint state."""
    for state in iter_states_of_kinds(problem_id, session_id, db_session, (StateKind.CUMULUS_OBJ_CONSTRAINT,)):
        if isinstance(state, CumulusObjectiveConstraintState):
            return state.hard_constraint_ids, state.soft_constraint_ids
    return [], []


@router.post("/solve")
def solve_solutions(
    request: CumulusClassificationRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> CumulusClassificationResponse:
    """Solve the problem using the CUMULUS method."""
    db_session = context.db_session
    user = context.user
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    solver = check_solver(problem_db=problem_db)
    problem = Problem.from_problemdb(problem_db)

    try:
        scalarizations = [CumulusScalarization(s) for s in request.scalarizations]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    hard_ids, soft_ids = _get_objective_constraint_ids(
        problem_db.id, interactive_session.id if interactive_session else None, db_session
    )
    hard_constraints = [
        Constraint.model_validate(row, from_attributes=True)
        for row in db_session.exec(select(ConstraintDB).where(ConstraintDB.id.in_(hard_ids))).all()
    ] or None
    soft_constraints = [
        Constraint.model_validate(row, from_attributes=True)
        for row in db_session.exec(select(ConstraintDB).where(ConstraintDB.id.in_(soft_ids))).all()
    ] or None

    session_id = interactive_session.id if interactive_session else None
    scenario_model_id = _get_scenario_model_id(problem_db.id, session_id, db_session)
    scenario_model = _load_scenario_model(scenario_model_id, db_session) if scenario_model_id is not None else None

    results_by_scalarization = solve_sub_problems(
        problem=problem,
        current_objectives=request.current_objectives,
        reference_point=request.preference.aspiration_levels,
        scalarizations=scalarizations,
        scalarization_options=request.scalarization_options,
        solver=solver,
        solver_options=request.solver_options,
        hard_constraints=hard_constraints,
        soft_constraints=soft_constraints,
        scenario_model=scenario_model,
    )
    # Filter out infeasible scalarizations (None values); store only valid results.
    solver_results: list[SolverResults] = [r for r in results_by_scalarization.values() if r is not None]

    warnings: list[str] = []
    if (
        CumulusScalarization.CUMULONIMBUS in scalarizations
        and results_by_scalarization.get(CumulusScalarization.CUMULONIMBUS) is None
        and (hard_ids or soft_ids)
    ):
        kinds = ([f"{len(hard_ids)} hard"] if hard_ids else []) + ([f"{len(soft_ids)} soft"] if soft_ids else [])
        warnings.append(
            f"Cumulonimbus scalarization failed to find a feasible solution. "
            f"You have {' and '.join(kinds)} active objective constraint(s) that may conflict "
            f"with the current reference point. Consider loosening or removing the constraints."
        )

    cumulus_state = CumulusClassificationState(
        preferences=request.preference,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        current_objectives=request.current_objectives,
        scalarizations=request.scalarizations,
        original_problem_id=request.original_problem_id,
        scenario_model_id=scenario_model_id,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=cumulus_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    current_solutions: list[SolutionReference] = [
        SolutionReference(state=state, solution_index=i) for i, _ in enumerate(solver_results)
    ]
    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)

    return CumulusClassificationResponse(
        state_id=state.id,
        scenario_model_id=scenario_model_id,
        previous_preference=request.preference,
        previous_objectives=request.current_objectives,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
        warnings=warnings,
    )


@router.post("/initialize")
def initialize(
    request: CumulusInitializationRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> CumulusInitializationResponse:
    """Initialize the problem for the CUMULUS method."""
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
        state = db_session.exec(select(StateDB).where(StateDB.id == info.state_id)).first()
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

    effective_original_problem_id = (
        request.original_problem_id if request.original_problem_id is not None else request.problem_id
    )

    # Only associate a scenario model when a combined problem was actually built from one,
    # i.e., when the problem being initialized differs from the original problem.
    _scenario_model_id: int | None = None
    if effective_original_problem_id != request.problem_id:
        _orig_db = db_session.get(ProblemDB, effective_original_problem_id)
        if _orig_db is not None and _orig_db.scenario_models:
            _scenario_model_id = _orig_db.scenario_models[0].id

    initialization_state = CumulusInitializationState(
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_results=start_result,
        original_problem_id=effective_original_problem_id,
        scenario_model_id=_scenario_model_id,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=initialization_state,
        kind=StateKind.CUMULUS_INIT,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    current_solutions = [SolutionReference(state=state, solution_index=0)]
    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)
    session_id = interactive_session.id if interactive_session is not None else None
    hard_ids, soft_ids = _get_objective_constraint_ids(problem_db.id, session_id, db_session)

    return CumulusInitializationResponse(
        state_id=state.id,
        problem_id=problem_db.id,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
        hard_constraint_ids=hard_ids,
        soft_constraint_ids=soft_ids,
    )


@router.post("/save")
def save(
    request: CumulusSaveRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> CumulusSaveResponse:
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

    save_state = CumulusSaveState(
        solutions=updated_solutions + new_solutions,
        original_problem_id=request.original_problem_id,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
        kind=StateKind.CUMULUS_SAVE,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return CumulusSaveResponse(state_id=state.id)


@router.post("/get-or-initialize")
def get_or_initialize(  # noqa: C901
    request: CumulusInitializationRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> (
    CumulusInitializationResponse
    | CumulusClassificationResponse
    | CumulusFinalizeResponse
    | CumulusScenarioSetupResponse
):
    """Get the latest CUMULUS state if it exists, or initialize a new one if it doesn't.

    If the problem has associated scenarios and no uncertainty measures have been specified, a
    ``CumulusScenarioSetupResponse`` is returned so the frontend can ask the decision maker which
    aggregates to include.  When the frontend re-calls with ``uncertainty_measures`` populated, a
    combined multi-scenario problem is built, saved to the database, and used for initialization.
    """
    db_session = context.db_session
    user = context.user
    interactive_session = context.interactive_session
    problem_db = context.problem_db

    statement = (
        select(StateDB)
        .where(
            StateDB.problem_id == request.problem_id,
            StateDB.session_id == (interactive_session.id if interactive_session else user.active_session_id),
        )
        .order_by(StateDB.id.desc())
    )
    states = db_session.exec(statement).all()

    latest_state = None
    for state in states:
        if state.base_state is not None and state.base_state.kind in (
            StateKind.CUMULUS_SOLVE,
            StateKind.CUMULUS_INIT,
            StateKind.CUMULUS_FINAL,
            StateKind.CUMULUS_SAVE,
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

        if isinstance(latest_state.state, CumulusClassificationState):
            return CumulusClassificationResponse(
                state_id=latest_state.id,
                previous_preference=latest_state.state.preferences,
                previous_objectives=latest_state.state.current_objectives,
                current_solutions=current_solutions,
                saved_solutions=saved_solutions,
                all_solutions=all_solutions,
            )

        if isinstance(latest_state.state, CumulusFinalState):
            solution_index = latest_state.state.solution_result_index
            origin_state_id = latest_state.state.solution_origin_state_id

            final_solution_ref_res = SolutionReferenceResponse(
                solution_index=solution_index,
                state_id=origin_state_id,
                objective_values=latest_state.state.solver_results.optimal_objectives,
                variable_values=latest_state.state.solver_results.optimal_variables,
            )

            return CumulusFinalizeResponse(
                state_id=latest_state.id,
                final_solution=final_solution_ref_res,
                saved_solutions=saved_solutions,
                all_solutions=all_solutions,
            )

        # CumulusInitializationState or CumulusSaveState
        _session_id = interactive_session.id if interactive_session is not None else user.active_session_id
        hard_ids, soft_ids = _get_objective_constraint_ids(request.problem_id, _session_id, db_session)
        return CumulusInitializationResponse(
            state_id=latest_state.id,
            current_solutions=current_solutions,
            saved_solutions=saved_solutions,
            all_solutions=all_solutions,
            hard_constraint_ids=hard_ids,
            soft_constraint_ids=soft_ids,
        )

    # No existing state — check whether the problem has associated scenarios.
    scenario_models = problem_db.scenario_models
    if scenario_models:
        scenario_model_db = scenario_models[0]

        if request.uncertainty_measures is None:
            # Ask the frontend which uncertainty aggregates the DM wants to include.
            problem = Problem.from_problemdb(problem_db)
            # Include objectives from both the base problem and the scenario pool (e.g. f_3).
            seen: set[str] = set()
            all_symbols: list[str] = []
            for sym in [obj.symbol for obj in problem.objectives] + [
                obj.symbol for obj in scenario_model_db.objectives
            ]:
                if sym not in seen:
                    seen.add(sym)
                    all_symbols.append(sym)
            return CumulusScenarioSetupResponse(
                scenario_model_id=scenario_model_db.id,
                objective_symbols=all_symbols,
            )

        if not request.uncertainty_measures:
            # DM explicitly declined to use scenarios — initialize with the original problem.
            return initialize(request, context)

        # The DM has chosen measures — build and persist the combined scenario problem.
        problem = Problem.from_problemdb(problem_db)
        mods = ProblemModification(uncertainty_measures=request.uncertainty_measures)
        try:
            combined_problem = apply_problem_modifications(problem, mods, db_session)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to build combined scenario problem: {e}",
            ) from e

        # Estimate ideal/nadir via payoff table so scalarizations are well-scaled.
        solver = check_solver(problem_db=problem_db)
        try:
            estimated_ideal, estimated_nadir = payoff_table_method(combined_problem, solver)
            combined_problem = combined_problem.update_ideal_and_nadir(estimated_ideal, estimated_nadir)
        except Exception:  # noqa: S110
            pass  # proceed without ideal/nadir if payoff table fails

        new_problem_db = ProblemDB.from_problem(combined_problem, user=user)
        new_problem_db.parent_problem_id = problem_db.id
        if request.name:
            new_problem_db.name = request.name
        original_desc = problem_db.description or ""
        combined_desc = new_problem_db.description or ""
        if original_desc and combined_desc != original_desc:
            new_problem_db.description = original_desc + "\n\n" + combined_desc
        db_session.add(new_problem_db)
        db_session.commit()
        db_session.refresh(new_problem_db)
        copy_problem_metadata(problem_db, new_problem_db, db_session)
        db_session.commit()

        new_context = SessionContext(
            user=user,
            db_session=db_session,
            problem_db=new_problem_db,
            interactive_session=interactive_session,
            parent_state=context.parent_state,
        )
        new_request = request.model_copy(
            update={
                "problem_id": new_problem_db.id,
                "original_problem_id": request.original_problem_id or request.problem_id,
                "uncertainty_measures": None,
            }
        )
        return initialize(new_request, new_context)

    return initialize(request, context)


@router.post("/finalize")
def finalize(
    request: CumulusFinalizeRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> CumulusFinalizeResponse:
    """Finalize the CUMULUS process by selecting a solution."""
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

    final_state = CumulusFinalState(
        solution_origin_state_id=solution_state_id,
        solution_result_index=solution_index,
        solver_results=actual_state.solver_results[solution_index],
        original_problem_id=request.original_problem_id,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=final_state,
        kind=StateKind.CUMULUS_FINAL,
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

    return CumulusFinalizeResponse(
        state_id=state.id,
        final_solution=solution_reference_response,
        saved_solutions=collect_saved_solutions(user=user, problem_id=problem_db.id, session=db_session),
        all_solutions=collect_all_solutions(user=user, problem_id=problem_db.id, session=db_session),
    )


@router.post("/intermediate")
def solve_intermediate(
    request: IntermediateSolutionRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> CumulusIntermediateSolutionResponse:
    """Solve intermediate solutions between two solutions using rpm_intermediate_solutions."""
    db_session = context.db_session
    user = context.user
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    var_and_obj_values_of_references: list[tuple[dict, dict]] = []
    reference_states = []

    for solution_info in [request.reference_solution_1, request.reference_solution_2]:
        solution_state = db_session.exec(select(StateDB).where(StateDB.id == solution_info.state_id)).first()

        if solution_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find a state with id={solution_info.state_id}.",
            )

        reference_states.append(solution_state)

        try:
            _var_values = solution_state.state.result_variable_values
            var_values = _var_values[solution_info.solution_index]
        except IndexError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The index {solution_info.solution_index} is out of bounds "
                "for results with len={len(_var_values)}",
            ) from exc

        try:
            _obj_values = solution_state.state.result_objective_values
            obj_values = _obj_values[solution_info.solution_index]
        except IndexError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The index {solution_info.solution_index} is out of bounds "
                "for results with len={len(_obj_values)}",
            ) from exc

        var_and_obj_values_of_references.append((var_values, obj_values))

    problem = Problem.from_problemdb(problem_db)
    solver = check_solver(problem_db=problem_db)

    solver_results: list[SolverResults] = rpm_intermediate_solutions(
        problem=problem,
        solution_1=var_and_obj_values_of_references[0][1],
        solution_2=var_and_obj_values_of_references[1][1],
        num_desired=request.num_desired or 1,
        scalarization_options=request.scalarization_options,
        solver=solver,
        solver_options=request.solver_options,
    )

    intermediate_state = IntermediateSolutionState(
        scalarization_options=request.scalarization_options,
        context="cumulus",
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        num_desired=request.num_desired or 1,
        reference_solution_1=var_and_obj_values_of_references[0][1],
        reference_solution_2=var_and_obj_values_of_references[1][1],
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=intermediate_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    saved_solutions = collect_saved_solutions(user, request.problem_id, db_session)
    all_solutions = collect_all_solutions(user, request.problem_id, db_session)

    return CumulusIntermediateSolutionResponse(
        state_id=state.id,
        reference_solution_1=var_and_obj_values_of_references[0][1],
        reference_solution_2=var_and_obj_values_of_references[1][1],
        current_solutions=[SolutionReference(state=state, solution_index=i) for i in range(state.state.num_solutions)],
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
    )


@router.post("/delete_save")
def delete_save(
    request: CumulusDeleteSaveRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard().post)],
) -> CumulusDeleteSaveResponse:
    """Delete a saved CUMULUS solution."""
    db_session = context.db_session

    to_be_deleted = db_session.exec(
        select(UserSavedSolutionDB).where(
            UserSavedSolutionDB.origin_state_id == request.state_id,
            UserSavedSolutionDB.solution_index == request.solution_index,
        )
    ).first()

    if to_be_deleted is None:
        raise HTTPException(detail="Unable to find a saved solution!", status_code=status.HTTP_404_NOT_FOUND)

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
            detail="Could not delete the saved solution!", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return CumulusDeleteSaveResponse(message="Save deleted.")


@router.post("/objective-constraint")
def set_objective_constraints(
    request: CumulusObjectiveConstraintRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> CumulusObjectiveConstraintResponse:
    """Set (replace) the list of objective constraints for the current CUMULUS session.

    Creates ConstraintDB rows in the database without adding them to the active problem.
    A new state records the IDs of the current constraint list.
    """
    db_session = context.db_session
    interactive_session = context.interactive_session
    parent_state = context.parent_state
    problem_db = context.problem_db

    hard_constraints: list[ConstraintDB] = []
    for raw in request.hard_constraints:
        try:
            constraint_db = ConstraintDB.model_validate(raw)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
        constraint_db.id = None
        constraint_db.problem_id = None
        db_session.add(constraint_db)
        hard_constraints.append(constraint_db)

    soft_constraints: list[ConstraintDB] = []
    for raw in request.soft_constraints:
        try:
            constraint_db = ConstraintDB.model_validate(raw)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
        constraint_db.id = None
        constraint_db.problem_id = None
        db_session.add(constraint_db)
        soft_constraints.append(constraint_db)

    db_session.flush()
    hard_constraint_ids = [c.id for c in hard_constraints]
    soft_constraint_ids = [c.id for c in soft_constraints]

    obj_constraint_state = CumulusObjectiveConstraintState(
        problem_id=problem_db.id,
        original_problem_id=request.original_problem_id,
        hard_constraint_ids=hard_constraint_ids,
        soft_constraint_ids=soft_constraint_ids,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=obj_constraint_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return CumulusObjectiveConstraintResponse(
        state_id=state.id,
        hard_constraint_ids=hard_constraint_ids,
        soft_constraint_ids=soft_constraint_ids,
    )


def _run_payoff_table_background(new_problem_id: int, cumulus_state_id: int, solver_class) -> None:
    """Background task: run payoff table on the newly created problem and update ideal/nadir + state."""
    try:
        with Session(engine) as session:
            problem_db = session.get(ProblemDB, new_problem_id)
            mod_state = session.get(CumulusModificationState, cumulus_state_id)
            if problem_db is None or mod_state is None:
                return

            problem = Problem.from_problemdb(problem_db)
            effective_solver = solver_class if solver_class is not None else guess_best_solver(problem)

            error_msg = None
            try:
                estimated_ideal, estimated_nadir = payoff_table_method(problem, solver=effective_solver)
                for obj_db in problem_db.objectives:
                    if obj_db.symbol in estimated_ideal:
                        obj_db.ideal = estimated_ideal[obj_db.symbol]
                    if obj_db.symbol in estimated_nadir:
                        obj_db.nadir = estimated_nadir[obj_db.symbol]
                    session.add(obj_db)
            except Exception as e:
                error_msg = str(e)

            mod_state.is_ready = True
            mod_state.error = error_msg
            session.add(mod_state)
            session.commit()
    except Exception:  # noqa: S110
        # Background tasks cannot surface errors to the caller; is_ready stays False.
        pass


@router.post("/modify-problem")
def modify_problem(
    request: CumulusModificationRequest,
    background_tasks: BackgroundTasks,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> CumulusModificationResponse:
    """Apply modifications to the current problem, verify feasibility, and save as a new problem."""
    db_session = context.db_session
    user = context.user
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    problem = Problem.from_problemdb(problem_db)
    modified_problem = apply_problem_modifications(problem, request.modifications, db_session)

    # Save the modified problem immediately (ideal/nadir will be updated by the background task)
    new_problem_db = ProblemDB.from_problem(modified_problem, user=user)
    new_problem_db.parent_problem_id = problem_db.id
    if request.name is not None:
        new_problem_db.name = request.name
    original_desc = problem_db.description or ""
    modified_desc = new_problem_db.description or ""
    if original_desc and modified_desc != original_desc:
        new_problem_db.description = original_desc + "\n\n" + modified_desc
    db_session.add(new_problem_db)
    db_session.commit()
    db_session.refresh(new_problem_db)
    copy_problem_metadata(problem_db, new_problem_db, db_session)
    db_session.commit()

    original_problem_id = request.original_problem_id if request.original_problem_id is not None else problem_db.id

    mod_session_id = interactive_session.id if interactive_session else None
    mod_scenario_model_id = _get_scenario_model_id(problem_db.id, mod_session_id, db_session)

    modification_state = CumulusModificationState(
        problem_id=new_problem_db.id,
        original_problem_id=original_problem_id,
        scenario_model_id=mod_scenario_model_id,
        is_ready=False,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=new_problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=modification_state,
    )

    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    solver_class = check_solver(problem_db=problem_db)

    background_tasks.add_task(
        _run_payoff_table_background,
        new_problem_db.id,
        state.base_state.id,
        solver_class,
    )

    return CumulusModificationResponse(
        state_id=state.id,
        problem_id=new_problem_db.id,
        original_problem_id=original_problem_id,
        scenario_model_id=mod_scenario_model_id,
        is_ready=False,
    )


@router.get("/modify-problem/status/{state_id}")
def modify_problem_status(
    state_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> CumulusModificationResponse:
    """Poll the status of a pending modify-problem operation."""
    state = db_session.exec(select(StateDB).where(StateDB.id == state_id)).first()
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"State {state_id} not found.")

    mod_state = state.state
    if not isinstance(mod_state, CumulusModificationState):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State {state_id} is not a Cumulus modification state.",
        )

    return CumulusModificationResponse(
        state_id=state_id,
        scenario_model_id=mod_state.scenario_model_id,
        problem_id=mod_state.problem_id,
        original_problem_id=mod_state.original_problem_id,
        is_ready=mod_state.is_ready,
        error=mod_state.error,
    )
