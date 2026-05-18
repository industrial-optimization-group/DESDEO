"""Defines end-points to access functionalities related to the CUMULUS method."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import engine, get_session
from desdeo.api.models import (
    CumulusFinalState,
    CumulusInitializationState,
    CumulusModificationState,
    CumulusSaveState,
    IntermediateSolutionRequest,
    IntermediateSolutionState,
    ReferencePoint,
    ScenarioModelDB,
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
    CumulusSaveRequest,
    CumulusSaveResponse,
)
from desdeo.api.models.generic import SolutionInfo
from desdeo.api.models.generic_states import SolutionReference, SolutionReferenceResponse, StateKind
from desdeo.api.models.problem import ProblemDB
from desdeo.api.models.state import CumulusClassificationState
from desdeo.api.routers.nimbus import collect_all_solutions, collect_saved_solutions
from desdeo.api.routers.problem import check_solver
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.cumulus import CumulusScalarization, generate_starting_point, solve_sub_problems
from desdeo.mcdm.reference_point_method import rpm_intermediate_solutions
from desdeo.problem import Problem
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ExtraFunction,
    Objective,
    ScalarizationFunction,
    TensorConstant,
    TensorVariable,
    Variable,
)
from desdeo.problem.utils import ProblemUtilsError, add_soft_constraint
from desdeo.tools import SolverResults, guess_best_solver
from desdeo.tools.robust import add_weighted_scenarios, add_worst_case_robust
from desdeo.tools.scenarios import build_combined_scenario_problem
from desdeo.tools.stochastic import add_conditional_value_at_risk, add_expected_value
from desdeo.tools.utils import payoff_table_method

from .utils import ContextField, SessionContext, SessionContextGuard

router = APIRouter(prefix="/method/cumulus")


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

    solver_results: list[SolverResults] = solve_sub_problems(
        problem=problem,
        current_objectives=request.current_objectives,
        reference_point=request.preference.aspiration_levels,
        scalarizations=scalarizations,
        scalarization_options=request.scalarization_options,
        solver=solver,
        solver_options=request.solver_options,
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
        previous_preference=request.preference,
        previous_objectives=request.current_objectives,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
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

    initialization_state = CumulusInitializationState(
        reference_point=starting_point,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_results=start_result,
        original_problem_id=request.original_problem_id
        if request.original_problem_id is not None
        else request.problem_id,
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

    return CumulusInitializationResponse(
        state_id=state.id,
        current_solutions=current_solutions,
        saved_solutions=saved_solutions,
        all_solutions=all_solutions,
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
def get_or_initialize(
    request: CumulusInitializationRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> CumulusInitializationResponse | CumulusClassificationResponse | CumulusFinalizeResponse:
    """Get the latest CUMULUS state if it exists, or initialize a new one if it doesn't."""
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

        # NIMBUSInitializationState
        return CumulusInitializationResponse(
            state_id=latest_state.id,
            current_solutions=current_solutions,
            saved_solutions=saved_solutions,
            all_solutions=all_solutions,
        )

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
                detail=f"The index {solution_info.solution_index} is out of bounds for results with len={len(_var_values)}",
            ) from exc

        try:
            _obj_values = solution_state.state.result_objective_values
            obj_values = _obj_values[solution_info.solution_index]
        except IndexError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The index {solution_info.solution_index} is out of bounds for results with len={len(_obj_values)}",
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
    except Exception:
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
    mods = request.modifications

    symbol_to_type = problem.get_symbol_type_map()

    def _parse_variable(d: dict) -> Variable | TensorVariable:
        if "shape" in d:
            return TensorVariable.model_validate(d, by_name=True)
        return Variable.model_validate(d, by_name=True)

    def _parse_constant(d: dict) -> Constant | TensorConstant:
        if "shape" in d:
            return TensorConstant.model_validate(d, by_name=True)
        return Constant.model_validate(d, by_name=True)

    type_parsers = {
        "variables": _parse_variable,
        "constants": _parse_constant,
        "objectives": lambda d: Objective.model_validate(d, by_name=True),
        "constraints": lambda d: Constraint.model_validate(d, by_name=True),
        "extra_funcs": lambda d: ExtraFunction.model_validate(d, by_name=True),
        "scalarization_funcs": lambda d: ScalarizationFunction.model_validate(d, by_name=True),
    }

    parsed_mods: dict[str, list] = {k: [] for k in type_parsers}
    mod_fields = [
        ("variables", mods.variables),
        ("constants", mods.constants),
        ("objectives", mods.objectives),
        ("constraints", mods.constraints),
        ("extra_funcs", mods.extra_funcs),
        ("scalarization_funcs", mods.scalarization_funcs),
    ]

    for field_name, raw_list in mod_fields:
        if not raw_list:
            continue
        for raw in raw_list:
            raw_dict = raw if isinstance(raw, dict) else raw.model_dump()
            try:
                element = type_parsers[field_name](raw_dict)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to parse '{field_name}' element: {e}",
                ) from e

            sym = element.symbol
            if sym in symbol_to_type and symbol_to_type[sym] != field_name:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Symbol '{sym}' already exists as type '{symbol_to_type[sym]}';"
                        f" cannot modify it as '{field_name}'."
                    ),
                )
            parsed_mods[field_name].append(element)

    def _merge(existing: list, new_elements: list) -> list:
        by_symbol = {e.symbol: e for e in existing}
        for elem in new_elements:
            by_symbol[elem.symbol] = elem
        return list(by_symbol.values())

    new_variables = _merge(problem.variables, parsed_mods["variables"])
    new_objectives = _merge(problem.objectives, parsed_mods["objectives"])

    merged_constants = _merge(problem.constants or [], parsed_mods["constants"])
    new_constants = merged_constants or None

    merged_constraints = _merge(problem.constraints or [], parsed_mods["constraints"])
    new_constraints = merged_constraints or None

    merged_extra = _merge(problem.extra_funcs or [], parsed_mods["extra_funcs"])
    new_extra_funcs = merged_extra or None

    # Scalarization functions may have None symbols; only named ones are merged by symbol
    existing_named_scal = {s.symbol: s for s in (problem.scalarization_funcs or []) if s.symbol is not None}
    existing_unnamed_scal = [s for s in (problem.scalarization_funcs or []) if s.symbol is None]
    for s in parsed_mods["scalarization_funcs"]:
        if s.symbol is not None:
            existing_named_scal[s.symbol] = s
        else:
            existing_unnamed_scal.append(s)
    merged_scal = list(existing_named_scal.values()) + existing_unnamed_scal
    new_scal_funcs = merged_scal or None

    try:
        modified_problem = problem.model_copy(
            update={
                "variables": new_variables,
                "constants": new_constants,
                "objectives": new_objectives,
                "constraints": new_constraints,
                "extra_funcs": new_extra_funcs,
                "scalarization_funcs": new_scal_funcs,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    # Apply soft constraints
    for soft_spec in mods.soft_constraints or []:
        constraint = next(
            (c for c in (modified_problem.constraints or []) if c.symbol == soft_spec.constraint_symbol),
            None,
        )
        if constraint is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Constraint '{soft_spec.constraint_symbol}' not found in the problem.",
            )
        try:
            modified_problem, _ = add_soft_constraint(
                modified_problem,
                constraint,
                symbol=soft_spec.violation_symbol,
                lte_violation_symbol=soft_spec.lte_violation_symbol,
                gte_violation_symbol=soft_spec.gte_violation_symbol,
            )
        except ProblemUtilsError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    # Apply uncertainty measures (all must share the same scenario_model_id)
    if mods.uncertainty_measures:
        sm_ids = {spec.scenario_model_id for spec in mods.uncertainty_measures}
        if len(sm_ids) > 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All uncertainty measures in a single request must reference the same scenario_model_id.",
            )
        sm_id = next(iter(sm_ids))
        scenario_model_db = db_session.get(ScenarioModelDB, sm_id)
        if scenario_model_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ScenarioModelDB with id={sm_id} not found.",
            )
        scenario_model = scenario_model_db.to_scenario_model(base_problem=modified_problem)
        combined, symbol_maps = build_combined_scenario_problem(scenario_model)
        for spec in mods.uncertainty_measures:
            try:
                if spec.measure_type == "expected_value":
                    combined, _ = add_expected_value(
                        scenario_model,
                        spec.symbols,
                        prefix=spec.prefix or "E_",
                        combined=combined,
                        symbol_maps=symbol_maps,
                    )
                elif spec.measure_type == "worst_case_robust":
                    combined, _ = add_worst_case_robust(
                        scenario_model,
                        spec.symbols,
                        prefix=spec.prefix or "robust_",
                        combined=combined,
                        symbol_maps=symbol_maps,
                    )
                elif spec.measure_type == "conditional_value_at_risk":
                    if spec.alpha is None:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="'alpha' is required for 'conditional_value_at_risk'.",
                        )
                    combined, _ = add_conditional_value_at_risk(
                        scenario_model,
                        spec.symbols,
                        alpha=spec.alpha,
                        cvar_prefix=spec.prefix or "CVAR_",
                        combined=combined,
                        symbol_maps=symbol_maps,
                    )
                elif spec.measure_type == "weighted_scenarios":
                    if spec.leaf_weights is None:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="'leaf_weights' is required for 'weighted_scenarios'.",
                        )
                    combined, _ = add_weighted_scenarios(
                        scenario_model,
                        spec.symbols,
                        weights=spec.leaf_weights,
                        prefix=spec.prefix or "weighted_",
                        combined=combined,
                        symbol_maps=symbol_maps,
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to apply uncertainty measure '{spec.measure_type}': {e}",
                ) from e
        modified_problem = combined

    # Save the modified problem immediately (ideal/nadir will be updated by the background task)
    new_problem_db = ProblemDB.from_problem(modified_problem, user=user)
    new_problem_db.parent_problem_id = problem_db.id
    db_session.add(new_problem_db)
    db_session.commit()
    db_session.refresh(new_problem_db)

    original_problem_id = request.original_problem_id if request.original_problem_id is not None else problem_db.id

    modification_state = CumulusModificationState(
        problem_id=new_problem_db.id,
        original_problem_id=original_problem_id,
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
        problem_id=mod_state.problem_id,
        original_problem_id=mod_state.original_problem_id,
        is_ready=mod_state.is_ready,
        error=mod_state.error,
    )
