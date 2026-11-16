"""Defines end-points of the JINA method for finding designs of scenario-based problems."""

import logging
import threading
from collections import OrderedDict
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, select

from desdeo.api.db import get_session
from desdeo.api.models import ProblemDB, StateDB, User
from desdeo.api.models.generic_states import StateKind
from desdeo.api.models.jina import (
    JinaAntifragilityRequest,
    JinaAntifragilityResponse,
    JinaDesign,
    JinaDesignInfo,
    JinaEvaluateRequest,
    JinaEvaluateResult,
    JinaGetOrInitializeResponse,
    JinaImportRequest,
    JinaIterateRequest,
    JinaIterateResult,
    JinaIterateStateResult,
    JinaScenarioModelInfo,
    JinaSelectRequest,
    JinaSelectResult,
    JinaSessionRequest,
    JinaSetupRequest,
    JinaSetupResult,
    JinaStateResponse,
)
from desdeo.api.models.problem import RepresentativeNonDominatedSolutions
from desdeo.api.models.scenario import ScenarioModelDB
from desdeo.api.models.state import JinaEvaluateState, JinaIterateState, JinaSelectState, JinaSetupState
from desdeo.api.routers.problem import check_solver
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.jina import (
    JinaProblem,
    View,
    build_jina_problem,
    leaf_ranges,
    match_pool,
    objective_ranges,
    solve_variants,
    target_ranges,
    target_values,
)
from desdeo.problem import ScenarioModel, TensorVariable
from desdeo.tools import guess_best_solver
from desdeo.tools.generics import BaseSolver
from desdeo.tools.robustness_metrics import antifragile_objectives, antifragility, domain_criterion
from desdeo.tools.scenario_designs import (
    LeafOutcome,
    default_design_variables,
    evaluate_design,
    find_design,
    root_variables,
)

from .utils import ContextField, SessionContext, SessionContextGuard, _may_access_state, load_scenario_model

router = APIRouter(prefix="/method/jina")
logger = logging.getLogger(__name__)

VIEWS: tuple[View, ...] = ("aggregated", "per_scenario")

_RESULT_MODELS = {
    StateKind.JINA_SETUP: JinaSetupResult,
    StateKind.JINA_ITERATE: JinaIterateStateResult,
    StateKind.JINA_EVALUATE: JinaEvaluateResult,
    StateKind.JINA_SELECT: JinaSelectResult,
}

# Built JINA problems by (problem_id, scenario_model_id, view, measure, cvar_alpha), least recently used first.
_CACHE_SIZE = 8
_cache: OrderedDict[tuple, JinaProblem] = OrderedDict()
_cache_lock = threading.Lock()
_key_locks: dict[tuple, threading.Lock] = {}
# Serialises registry writes within the process; the setup row is also locked in the database.
_registry_lock = threading.Lock()


def _jina_problem(problem_id: int, setup: JinaSetupResult, view: View, model: ScenarioModel) -> JinaProblem:
    """Return the JINA problem of a setup and view from the cache, building it once if missing."""
    # The per-scenario view aggregates nothing, so it does not depend on the measure.
    measure, cvar_alpha = (setup.measure, setup.cvar_alpha) if view == "aggregated" else ("worst_case", 0.9)
    key = (problem_id, setup.scenario_model_id, view, measure, cvar_alpha)
    with _cache_lock:
        key_lock = _key_locks.setdefault(key, threading.Lock())
    with key_lock:
        with _cache_lock:
            if key in _cache:
                _cache.move_to_end(key)
                return _cache[key]
        jp = build_jina_problem(model, view, measure, cvar_alpha=cvar_alpha)
        with _cache_lock:
            _cache[key] = jp
            while len(_cache) > _CACHE_SIZE:
                _key_locks.pop(_cache.popitem(last=False)[0], None)
    return jp


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _leaf_solver(model: ScenarioModel) -> type[BaseSolver]:
    """Guess a solver for the leaf problems of a scenario model."""
    return guess_best_solver(model.get_scenario_problem(next(iter(model.leaf_scenarios))))


def _load_model(scenario_model_id: int, problem_db: ProblemDB, db_session: Session) -> ScenarioModel:
    """Load a scenario model of the problem; raise 422 if it is not one."""
    sm_db = db_session.get(ScenarioModelDB, scenario_model_id)
    if sm_db is None or sm_db.base_problem_id != problem_db.id:
        raise _unprocessable(f"Scenario model {scenario_model_id} is not a scenario model of problem {problem_db.id}.")
    return load_scenario_model(scenario_model_id, db_session)


def _objective_symbols(model: ScenarioModel) -> set[str]:
    return {obj.symbol for obj in [*model.base_problem.objectives, *model.objectives]}


def _leaf_objectives(model: ScenarioModel) -> dict[str, set[str]]:
    return {leaf: {obj.symbol for obj in model.get_scenario_problem(leaf).objectives} for leaf in model.leaf_scenarios}


def _get_state(
    state_id: int, user: User, db_session: Session, kinds: tuple[StateKind, ...] = tuple(_RESULT_MODELS)
) -> StateDB:
    """Return a state of one of ``kinds``; raise 404 if there is none or the user may not access it."""
    state = db_session.get(StateDB, state_id)
    if (
        state is None
        or state.base_state is None
        or state.base_state.kind not in kinds
        or not _may_access_state(user, state, db_session)
    ):
        raise _not_found(f"No JINA state with id={state_id}.")
    return state


def _problem_state(state_id: int, kind: StateKind, context: SessionContext) -> StateDB:
    """Return a state of ``kind`` of the context's problem; raise 404 otherwise."""
    state = _get_state(state_id, context.user, context.db_session, (kind,))
    if state.problem_id != context.problem_db.id:
        raise _not_found(f"No {kind.value} state with id={state_id} in problem {context.problem_db.id}.")
    return state


def _result(sub: SQLModel, kind: StateKind) -> BaseModel:
    """Return the contents of a JINA substate as its result model, detached from the database."""
    model = _RESULT_MODELS[kind]
    return model.model_validate(
        {name: getattr(sub, name) for name in model.model_fields if name != "kind"} | {"kind": kind.value}
    )


def _snapshot(setup: JinaSetupState) -> JinaSetupResult:
    """Return the contents of a setup state, detached from the database."""
    return _result(setup, StateKind.JINA_SETUP)


def _get_setup(setup_state_id: int, context: SessionContext, *, ready: bool = True) -> tuple[StateDB, JinaSetupResult]:
    """Return a setup state of the context with its contents; with ``ready``, raise if its ranges are not ready.

    Raises 409 if the ranges are still being computed and 422 if computing them failed.
    """
    state = _problem_state(setup_state_id, StateKind.JINA_SETUP, context)
    sub = state.state
    if ready and not sub.is_ready:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The JINA setup is not ready yet.")
    if ready and sub.error is not None:
        raise _unprocessable(f"The JINA setup failed: {sub.error}")
    return state, _snapshot(sub)


def _parent_id(request: JinaSessionRequest, default: int | None) -> int | None:
    return request.parent_state_id if request.parent_state_id is not None else default


def _child_states(setup_state_id: int, db_session: Session, tables: tuple[type[SQLModel], ...]) -> list[StateDB]:
    """Return the states of the given JINA tables that belong to a setup, oldest first."""
    states = [
        state
        for table in tables
        for state in db_session.exec(
            select(StateDB).join(table, table.id == StateDB.state_id).where(table.setup_state_id == setup_state_id)
        ).all()
    ]
    return sorted(states, key=lambda state: state.id)


def _iterate_states(setup_state_id: int, db_session: Session) -> list[StateDB]:
    return _child_states(setup_state_id, db_session, (JinaIterateState,))


def _registry(iterate_states: list[StateDB]) -> list[tuple[int, JinaDesign]]:
    """Return the designs added by iterate states with the StateDB id of the state that added each."""
    return [(state.id, JinaDesign.model_validate(design)) for state in iterate_states for design in state.state.designs]


def _register(
    candidates: list[JinaDesign], registry: list[JinaDesign], model: ScenarioModel, rtol: float, next_id: int
) -> tuple[list[int], list[JinaDesign], int]:
    """Match candidates against the registry and each other.

    Returns:
        The id of each candidate, the candidates new to the registry with new ids from ``next_id``
        on, and the next unused id.
    """
    registry = list(registry)
    variables = {var.symbol: var for var in model.variables} | {var.symbol: var for var in model.base_problem.variables}
    ids: list[int] = []
    new: list[JinaDesign] = []
    for candidate in candidates:
        index = find_design([design.values for design in registry], candidate.values, variables, rtol=rtol)
        if index is None:
            design = candidate.model_copy(update={"id": next_id})
            next_id += 1
            registry.append(design)
            new.append(design)
            ids.append(design.id)
        else:
            ids.append(registry[index].id)
    return ids, new, next_id


def _store_designs(
    session: Session, setup_id: int, setup_state_id: int, candidates: list[JinaDesign], model: ScenarioModel
) -> tuple[list[int], list[JinaDesign]]:
    """Give candidates registry ids with the setup row locked; the caller stores the new designs and commits."""
    setup = session.exec(select(JinaSetupState).where(JinaSetupState.id == setup_id).with_for_update()).one()
    registry = [design for _, design in _registry(_iterate_states(setup_state_id, session))]
    ids, new, setup.next_design_id = _register(candidates, registry, model, setup.design_rtol, setup.next_design_id)
    session.add(setup)
    return ids, new


def _state_response(state: StateDB) -> JinaStateResponse:
    sub = state.state
    kind = state.base_state.kind
    return JinaStateResponse(
        state_id=state.id,
        kind=kind,
        is_ready=getattr(sub, "is_ready", True),
        error=getattr(sub, "error", None),
        result=_result(sub, kind),
    )


def _create_state(context: SessionContext, sub: SQLModel, parent_id: int | None) -> StateDB:
    state = StateDB.create(
        database_session=context.db_session,
        problem_id=context.problem_db.id,
        session_id=context.interactive_session.id if context.interactive_session is not None else None,
        parent_id=parent_id,
        state=sub,
    )
    context.db_session.commit()
    context.db_session.refresh(state)
    return state


def _uncovered_leaves(reference_point: dict[str, float], leaf_objectives: dict[str, set[str]]) -> list[str]:
    """Return the leaves where a reference point has no objective of the leaf."""
    return [leaf for leaf, objectives in leaf_objectives.items() if not objectives & set(reference_point)]


def _fail(session: Session, table: type[SQLModel], sub_id: int, error: Exception) -> None:
    """Record a failed background task on its state."""
    session.rollback()
    sub = session.get(table, sub_id)
    sub.error = f"{type(error).__name__}: {error}"
    sub.is_ready = True
    session.add(sub)
    session.commit()


def _run_setup(bind: Engine, problem_id: int, setup_id: int, solver: type[BaseSolver] | None) -> None:
    """Background task: compute the targets and target ranges of both views of a setup."""
    with Session(bind) as session:
        try:
            setup = _snapshot(session.get(JinaSetupState, setup_id))
            model = load_scenario_model(setup.scenario_model_id, session)
            session.commit()

            targets, ranges = {}, {}
            for view in VIEWS:
                jp = _jina_problem(problem_id, setup, view, model)
                targets[view] = [t.model_dump() for t in jp.targets]
                ranges[view] = target_ranges(jp, model, solver or guess_best_solver(jp.problem))

            sub = session.get(JinaSetupState, setup_id)
            sub.targets, sub.ranges, sub.is_ready = targets, ranges, True
            session.add(sub)
            session.commit()
        except Exception as e:
            _fail(session, JinaSetupState, setup_id, e)


def _run_solve(bind: Engine, problem_id: int, setup_id: int, iterate_id: int, solver: type[BaseSolver] | None) -> None:
    """Background task: solve the variants of an iterate state and add their designs to the registry."""
    with Session(bind) as session:
        try:
            setup = _snapshot(session.get(JinaSetupState, setup_id))
            iterate = session.get(JinaIterateState, iterate_id)
            setup_state_id, view, reference_point = iterate.setup_state_id, iterate.view, dict(iterate.reference_point)
            model = load_scenario_model(setup.scenario_model_id, session)
            session.commit()

            jp = _jina_problem(problem_id, setup, view, model)
            variants = solve_variants(
                jp,
                reference_point,
                setup.ranges[view],
                solver or guess_best_solver(jp.problem),
                design_variables=setup.design_variables,
            )
            solved = [variant for variant in variants if variant.success]
            candidates = [
                JinaDesign(
                    id=0,
                    values=variant.design,
                    effective_reference_point=variant.effective_reference_point,
                    view=view,
                    source="solve",
                    leaf_objectives=variant.leaf_objectives,
                )
                for variant in solved
            ]

            with _registry_lock:
                ids, new = _store_designs(session, setup_id, setup_state_id, candidates, model)
                design_ids = dict(zip([variant.name for variant in solved], ids, strict=True))
                iterate = session.get(JinaIterateState, iterate_id)
                iterate.results = [
                    JinaIterateResult(
                        **variant.model_dump(exclude={"leaf_objectives", "design"}),
                        design_id=design_ids.get(variant.name),
                    ).model_dump()
                    for variant in variants
                ]
                iterate.designs = [design.model_dump() for design in new]
                iterate.new_design_ids = [design.id for design in new]
                iterate.is_ready = True
                session.add(iterate)
                session.commit()
        except Exception as e:
            _fail(session, JinaIterateState, iterate_id, e)


def _run_import(
    bind: Engine, setup_id: int, iterate_id: int, representative_set_id: int, solver: type[BaseSolver] | None
) -> None:
    """Background task: evaluate the new designs of a representative solution set and add them to the registry."""
    with Session(bind) as session:
        try:
            setup = _snapshot(session.get(JinaSetupState, setup_id))
            iterate = session.get(JinaIterateState, iterate_id)
            setup_state_id, import_rp = iterate.setup_state_id, dict(iterate.reference_point)
            model = load_scenario_model(setup.scenario_model_id, session)
            data = session.get(RepresentativeNonDominatedSolutions, representative_set_id).solution_data
            registry = [design for _, design in _registry(_iterate_states(setup_state_id, session))]
            next_id = session.get(JinaSetupState, setup_id).next_design_id
            session.commit()

            rows = [
                JinaDesign(id=0, values={sym: data[sym][i] for sym in setup.design_variables}, source="import")
                for i in range(len(data[setup.design_variables[0]]))
            ]
            # Tells which rows are new and which repeat each other; the ids are assigned when storing.
            row_ids, first_rows, _ = _register(rows, registry, model, setup.design_rtol, next_id)

            solver = solver or _leaf_solver(model)
            ranges = leaf_ranges(setup.targets["per_scenario"], setup.ranges["per_scenario"])
            evaluated = []
            statuses = dict.fromkeys(row_ids, (True, "The design is already in the registry."))
            for row in first_rows:
                design = row.model_copy(update={"import_reference_point": import_rp})
                outcomes = evaluate_design(model, design.values, solver, reference_point=import_rp, leaf_ranges=ranges)
                failed = [leaf for leaf, outcome in outcomes.items() if not outcome.status]
                statuses[design.id] = (not failed, f"Evaluation failed in leaves {failed}." if failed else "Evaluated.")
                leaf_objectives = {leaf: outcome.objectives for leaf, outcome in outcomes.items() if outcome.status}
                evaluated.append(design.model_copy(update={"leaf_objectives": leaf_objectives}))

            with _registry_lock:
                ids, new = _store_designs(session, setup_id, setup_state_id, evaluated, model)
                final_ids = {design.id: final_id for design, final_id in zip(evaluated, ids, strict=True)}
                iterate = session.get(JinaIterateState, iterate_id)
                iterate.results = [
                    JinaIterateResult(
                        name=f"row_{i}",
                        success=statuses[row_id][0],
                        message=statuses[row_id][1],
                        design_id=final_ids.get(row_id, row_id),
                    ).model_dump()
                    for i, row_id in enumerate(row_ids)
                ]
                iterate.designs = [design.model_dump() for design in new]
                iterate.new_design_ids = [design.id for design in new]
                iterate.is_ready = True
                session.add(iterate)
                session.commit()
        except Exception as e:
            _fail(session, JinaIterateState, iterate_id, e)


def _run_evaluate(bind: Engine, setup_id: int, evaluate_id: int, solver: type[BaseSolver] | None) -> None:
    """Background task: evaluate designs of the registry in the leaves of a scenario model at the thresholds.

    Each leaf is re-solved with the design variables fixed, at the thresholds as reference point, with
    ASF weights from the setup's per-scenario target ranges combined per objective.  The domain
    criterion is computed from the leaves that were solved.
    """
    with Session(bind) as session:
        try:
            setup = _snapshot(session.get(JinaSetupState, setup_id))
            evaluate = session.get(JinaEvaluateState, evaluate_id)
            scenario_model_id, design_ids = evaluate.scenario_model_id, list(evaluate.design_ids)
            thresholds = dict(evaluate.thresholds)
            model = load_scenario_model(scenario_model_id, session)
            registry = {design.id: design for _, design in _registry(_iterate_states(evaluate.setup_state_id, session))}
            session.commit()

            solver = solver or _leaf_solver(model)
            objectives = _objective_symbols(model)
            ranges = {
                obj: r
                for obj, r in objective_ranges(setup.targets["per_scenario"], setup.ranges["per_scenario"]).items()
                if obj in objectives
            }
            outcomes, values = {}, {}
            for design_id in design_ids:
                design = registry[design_id]
                try:
                    result = evaluate_design(model, design.values, solver, reference_point=thresholds, ranges=ranges)
                except ValueError as e:
                    result = {leaf: LeafOutcome(status=False, message=str(e)) for leaf in model.leaf_scenarios}
                outcomes[str(design_id)] = {leaf: outcome.model_dump() for leaf, outcome in result.items()}
                values[design_id] = {leaf: outcome.objectives for leaf, outcome in result.items() if outcome.status}
            maximize = {obj.symbol: obj.maximize for obj in [*model.objectives, *model.base_problem.objectives]}
            domain = domain_criterion(values, maximize, thresholds)

            evaluate = session.get(JinaEvaluateState, evaluate_id)
            evaluate.outcomes, evaluate.is_ready = outcomes, True
            evaluate.domain_criterion = {str(design_id): dc.model_dump() for design_id, dc in domain.items()}
            session.add(evaluate)
            session.commit()
        except Exception as e:
            _fail(session, JinaEvaluateState, evaluate_id, e)


@router.get("/scenario-models")
def get_scenario_models(
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).get)],
) -> list[JinaScenarioModelInfo]:
    """List the scenario models of a problem; models that fail to load are left out."""
    infos = []
    for sm_db in list(context.problem_db.scenario_models):
        try:
            model = load_scenario_model(sm_db.id, context.db_session)
            root = root_variables(model)
            leaves = list(model.leaf_scenarios)
            infos.append(
                JinaScenarioModelInfo(
                    id=sm_db.id,
                    leaves=leaves,
                    n_leaves=len(leaves),
                    has_probabilities=bool(sm_db.scenario_probabilities),
                    root_variables=root,
                    default_design_variables=default_design_variables(model) if root else [],
                    objectives=list(
                        dict.fromkeys(obj.symbol for obj in [*model.base_problem.objectives, *model.objectives])
                    ),
                    maximize={obj.symbol: obj.maximize for obj in [*model.objectives, *model.base_problem.objectives]},
                )
            )
        except Exception:
            logger.exception("Scenario model %s of problem %s failed to load.", sm_db.id, context.problem_db.id)
            context.db_session.rollback()
    return infos


@router.post("/get-or-initialize")
def get_or_initialize(
    request: JinaSessionRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> JinaGetOrInitializeResponse:
    """Return the latest JINA setup of the session, or None, and all later JINA states of that setup."""
    interactive_session = context.interactive_session
    setup_state = context.db_session.exec(
        select(StateDB)
        .join(JinaSetupState, JinaSetupState.id == StateDB.state_id)
        .where(
            StateDB.problem_id == context.problem_db.id,
            StateDB.session_id == (interactive_session.id if interactive_session else context.user.active_session_id),
        )
        .order_by(StateDB.id.desc())
    ).first()
    if setup_state is None:
        return JinaGetOrInitializeResponse(setup=None, states=[])
    states = _child_states(setup_state.id, context.db_session, (JinaIterateState, JinaEvaluateState, JinaSelectState))
    return JinaGetOrInitializeResponse(
        setup=_state_response(setup_state), states=[_state_response(state) for state in states]
    )


@router.post("/setup")
def setup(
    request: JinaSetupRequest,
    background_tasks: BackgroundTasks,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> JinaStateResponse:
    """Start a JINA run on a scenario model of the problem; its target ranges are computed in the background."""
    problem_db = context.problem_db
    if not problem_db.scenario_models:
        raise _unprocessable(f"Problem {problem_db.id} has no scenario model.")
    scenario_model_id = (
        request.scenario_model_id if request.scenario_model_id is not None else problem_db.scenario_models[0].id
    )
    model = _load_model(scenario_model_id, problem_db, context.db_session)

    if request.design_variables is None:
        try:
            design_variables = default_design_variables(model)
        except ValueError as e:
            raise _unprocessable(str(e)) from e
    else:
        design_variables = request.design_variables
        if not design_variables or not set(design_variables) <= set(root_variables(model)):
            raise _unprocessable(
                f"Design variables must be a nonempty subset of the root variables {root_variables(model)}; "
                f"got {design_variables}."
            )
    variables = {var.symbol: var for var in model.variables} | {var.symbol: var for var in model.base_problem.variables}
    max_dims = 2
    if high := [
        sym
        for sym in design_variables
        if isinstance(variables[sym], TensorVariable) and len(variables[sym].shape) > max_dims
    ]:
        raise _unprocessable(f"Design variables {high} have more than two dimensions.")
    if request.baseline_leaf is not None and request.baseline_leaf not in model.leaf_scenarios:
        raise _unprocessable(
            f"'{request.baseline_leaf}' is not a leaf of the scenario model {list(model.leaf_scenarios)}."
        )

    setup = JinaSetupResult(
        kind="jina.setup",
        scenario_model_id=scenario_model_id,
        design_variables=design_variables,
        measure=request.measure,
        cvar_alpha=request.cvar_alpha,
        baseline_leaf=request.baseline_leaf,
        design_rtol=request.design_rtol,
        targets=None,
        ranges=None,
    )
    sub = JinaSetupState(**setup.model_dump(exclude={"kind", "targets", "ranges"}))
    state = _create_state(context, sub, request.parent_state_id)
    background_tasks.add_task(
        _run_setup, context.db_session.get_bind(), problem_db.id, state.base_state.id, check_solver(problem_db)
    )
    return _state_response(state)


@router.post("/iterate")
def iterate(
    request: JinaIterateRequest,
    background_tasks: BackgroundTasks,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> JinaStateResponse:
    """Solve new designs at a reference point in the background, or pick designs found earlier from the pool."""
    setup_state, setup = _get_setup(request.setup_state_id, context)
    targets = {t.symbol for t in setup.targets[request.view]}
    if not request.reference_point or not set(request.reference_point) <= targets:
        raise _unprocessable(
            f"The reference point must have targets of the {request.view} view {sorted(targets)}; "
            f"got {sorted(request.reference_point)}."
        )

    sub = JinaIterateState(
        setup_state_id=setup_state.id, mode=request.mode, view=request.view, reference_point=request.reference_point
    )
    if request.mode == "pool":
        model = load_scenario_model(setup.scenario_model_id, context.db_session)
        jp = _jina_problem(context.problem_db.id, setup, request.view, model)
        iterate_states = _iterate_states(setup_state.id, context.db_session)
        values = {design.id: target_values(jp, design.leaf_objectives) for _, design in _registry(iterate_states)}
        exclude = {
            result["design_id"]
            for state in iterate_states
            if state.state.mode == "pool"
            for result in state.state.results
        }
        try:
            picks = match_pool(values, request.reference_point, setup.ranges[request.view], jp.targets, exclude=exclude)
        except ValueError as e:
            raise _unprocessable(str(e)) from e
        sub.results = [
            JinaIterateResult(
                name=name,
                success=True,
                message="Picked from the design pool.",
                effective_reference_point=request.reference_point,
                target_values=values[design_id],
                design_id=design_id,
            ).model_dump()
            for design_id, names in picks.items()
            for name in names
        ]
        sub.is_ready = True

    state = _create_state(context, sub, _parent_id(request, setup_state.id))
    if request.mode == "solve":
        background_tasks.add_task(
            _run_solve,
            context.db_session.get_bind(),
            context.problem_db.id,
            setup_state.state_id,
            state.base_state.id,
            check_solver(context.problem_db),
        )
    return _state_response(state)


@router.post("/import")
def import_designs(
    request: JinaImportRequest,
    background_tasks: BackgroundTasks,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> JinaStateResponse:
    """Import the designs of a representative solution set of the problem; they are evaluated in the background."""
    setup_state, setup = _get_setup(request.setup_state_id, context)
    solutions = context.db_session.get(RepresentativeNonDominatedSolutions, request.representative_set_id)
    if solutions is None or solutions.metadata_instance.problem_id != context.problem_db.id:
        raise _unprocessable(
            f"Representative solution set {request.representative_set_id} is not a set of problem "
            f"{context.problem_db.id}."
        )
    if missing := [sym for sym in setup.design_variables if sym not in solutions.solution_data]:
        raise _unprocessable(f"The representative solution set has no columns for design variables {missing}.")
    model = load_scenario_model(setup.scenario_model_id, context.db_session)
    objectives = _objective_symbols(model)
    if not set(request.reference_point) <= objectives:
        raise _unprocessable(
            f"The reference point must have objectives of {sorted(objectives)}; got {sorted(request.reference_point)}."
        )
    if uncovered := _uncovered_leaves(request.reference_point, _leaf_objectives(model)):
        raise _unprocessable(f"The reference point has no objectives of leaves {uncovered}.")

    sub = JinaIterateState(setup_state_id=setup_state.id, mode="import", reference_point=request.reference_point)
    state = _create_state(context, sub, _parent_id(request, setup_state.id))
    background_tasks.add_task(
        _run_import,
        context.db_session.get_bind(),
        setup_state.state_id,
        state.base_state.id,
        request.representative_set_id,
        check_solver(context.problem_db),
    )
    return _state_response(state)


@router.post("/evaluate")
def evaluate(
    request: JinaEvaluateRequest,
    background_tasks: BackgroundTasks,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> JinaStateResponse:
    """Evaluate designs in the leaves of the setup's or another scenario model of the problem in the background.

    Every leaf is re-solved at the thresholds with the design variables fixed, and the domain criterion
    of each design at the thresholds is stored with the outcomes.  The thresholds must cover exactly
    the objectives of the scenario model.
    """
    setup_state, setup = _get_setup(request.setup_state_id, context)
    scenario_model_id = request.scenario_model_id if request.scenario_model_id is not None else setup.scenario_model_id
    model = _load_model(scenario_model_id, context.problem_db, context.db_session)
    if missing := sorted(set(setup.design_variables) - set(root_variables(model))):
        raise _unprocessable(
            f"Design variables {missing} are not root variables of scenario model {scenario_model_id}."
        )
    objectives = _objective_symbols(model)
    if set(request.thresholds) != objectives:
        raise _unprocessable(
            f"Thresholds must cover exactly the objectives of scenario model {scenario_model_id}; "
            f"missing {sorted(objectives - set(request.thresholds))}, "
            f"unknown {sorted(set(request.thresholds) - objectives)}."
        )

    registry = {design.id: design for _, design in _registry(_iterate_states(setup_state.id, context.db_session))}
    design_ids = list(registry) if request.design_ids is None else request.design_ids
    if not design_ids or not set(design_ids) <= set(registry):
        raise _unprocessable(f"Designs to evaluate must be a nonempty subset of {sorted(registry)}; got {design_ids}.")

    sub = JinaEvaluateState(
        setup_state_id=setup_state.id,
        scenario_model_id=scenario_model_id,
        design_ids=design_ids,
        thresholds=request.thresholds,
    )
    state = _create_state(context, sub, _parent_id(request, setup_state.id))
    background_tasks.add_task(
        _run_evaluate,
        context.db_session.get_bind(),
        setup_state.state_id,
        state.base_state.id,
        check_solver(context.problem_db),
    )
    return _state_response(state)


@router.get("/status/{state_id}")
def get_status(
    state_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> JinaStateResponse:
    """Return a JINA state and whether its background job has finished."""
    return _state_response(_get_state(state_id, user, db_session))


@router.post("/select")
def select_designs(
    request: JinaSelectRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> JinaStateResponse:
    """Store the wishlist and the final design of the decision maker."""
    setup_state, _ = _get_setup(request.setup_state_id, context, ready=False)
    registry = {design.id for _, design in _registry(_iterate_states(setup_state.id, context.db_session))}
    chosen = set(request.wishlist) | ({request.final_design_id} if request.final_design_id is not None else set())
    if unknown := sorted(chosen - registry):
        raise _unprocessable(f"Designs {unknown} are not in the registry.")
    sub = JinaSelectState(
        setup_state_id=setup_state.id, wishlist=request.wishlist, final_design_id=request.final_design_id
    )
    return _state_response(_create_state(context, sub, _parent_id(request, setup_state.id)))


@router.post("/antifragility")
def antifragility_analysis(
    request: JinaAntifragilityRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).post)],
) -> JinaAntifragilityResponse:
    """Compute the antifragility of evaluated designs relative to the setup's baseline leaf.

    The absolute and loss floors set the Taleb classes.  Leaves where a design failed are missing
    outcomes, treated by the metric's default policy.  Raises 422 if the setup has no baseline leaf
    or no selected design has an outcome in it.
    """
    setup_state, setup = _get_setup(request.setup_state_id, context, ready=False)
    evaluated = _problem_state(request.evaluate_state_id, StateKind.JINA_EVALUATE, context).state
    if evaluated.setup_state_id != setup_state.id:
        raise _unprocessable(f"Evaluate state {request.evaluate_state_id} is not of setup {setup_state.id}.")
    if not evaluated.is_ready:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The evaluation is not ready yet.")
    if evaluated.error is not None:
        raise _unprocessable(f"The evaluation failed: {evaluated.error}")

    outcomes = _result(evaluated, StateKind.JINA_EVALUATE).outcomes
    design_ids = list(outcomes) if request.design_ids is None else request.design_ids
    if not design_ids or not set(design_ids) <= set(outcomes):
        raise _unprocessable(
            f"Designs must be a nonempty subset of the evaluated {sorted(outcomes)}; got {design_ids}."
        )
    values = {
        design_id: {leaf: outcome.objectives for leaf, outcome in outcomes[design_id].items() if outcome.status}
        for design_id in design_ids
    }
    if setup.baseline_leaf is None:
        raise _unprocessable("The setup has no baseline leaf for the antifragility analysis.")
    if not any(setup.baseline_leaf in leaves for leaves in values.values()):
        raise _unprocessable(f"No selected design has an outcome in the baseline leaf '{setup.baseline_leaf}'.")
    model = load_scenario_model(evaluated.scenario_model_id, context.db_session)
    maximize = {obj.symbol: obj.maximize for obj in [*model.objectives, *model.base_problem.objectives]}

    try:
        fragility = antifragility(
            values,
            maximize,
            setup.baseline_leaf,
            absolute_floors=request.absolute_floors,
            loss_floors=request.loss_floors,
        )
    except ValueError as e:
        raise _unprocessable(str(e)) from e
    return JinaAntifragilityResponse(antifragility=fragility, antifragile_objectives=antifragile_objectives(fragility))


@router.get("/designs")
def get_designs(
    setup_state_id: int,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]).get)],
) -> list[JinaDesignInfo]:
    """List the design registry of a setup with the target values of each design in both views."""
    setup_state, setup = _get_setup(setup_state_id, context)
    model = load_scenario_model(setup.scenario_model_id, context.db_session)
    problems = {view: _jina_problem(setup_state.problem_id, setup, view, model) for view in VIEWS}
    return [
        JinaDesignInfo(
            **design.model_dump(),
            state_id=state_id,
            target_values={view: target_values(jp, design.leaf_objectives) for view, jp in problems.items()},
        )
        for state_id, design in _registry(_iterate_states(setup_state.id, context.db_session))
    ]
