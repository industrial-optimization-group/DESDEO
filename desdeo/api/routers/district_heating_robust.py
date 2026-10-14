"""Endpoints for the JINA multi-scenario robust interactive method.

Generic: every endpoint takes a `problem_id` and works against whatever problem that id points
to, provided it has an attached scenario model (see `district_heating_robust_data.get_context`
and `desdeo/api/db_init_district_heating.py` for how the district heating problem — the first,
no longer the only, problem this serves — got registered that way).

Live, worst-case robust solving over every scenario a problem defines. Unlike most generic
DESDEO methods, this one DOES build and solve a real `desdeo.problem.Problem` on every
iteration — but the Problem itself always comes from the standard `ProblemDB`/`ScenarioModelDB`
registry now, same as any other method.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    DistrictHeatingRobustAnalysisRequest,
    DistrictHeatingRobustAnalysisResponse,
    DistrictHeatingRobustCombinedScenarioRequest,
    DistrictHeatingRobustCombinedScenarioResponse,
    DistrictHeatingRobustIterateRequest,
    DistrictHeatingRobustIterateResponse,
    DistrictHeatingRobustIterationState,
    DistrictHeatingRobustMatchedSolution,
    DistrictHeatingRobustSessionTreeEntry,
    DistrictHeatingRobustStrategicDesignsResponse,
    DistrictHeatingRobustWishlistResponse,
    DistrictHeatingRobustWishlistState,
    DistrictHeatingRobustWishlistUpdateRequest,
    JinaObjectiveMeta,
    JinaProblemMeta,
    JinaScalarizerMeta,
    JinaStrategicVarMeta,
    StateDB,
    User,
)
from desdeo.api.models.generic_states import StateKind
from desdeo.api.routers.district_heating_robust_data import (
    JinaScenarioContext,
    JinaScenarioError,
    compute_wish_list_analysis,
    get_context,
    list_strategic_designs,
    run_iteration,
    strategic_axis_max,
)
from desdeo.api.routers.jina_compound import (
    compute_superadditivity,
    resolve_hook,
    run_compound_analysis,
    summarize_compound_results,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.routers.utils import fetch_interactive_session, fetch_parent_state, fetch_problem_with_role_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/method/district-heating-robust")

# NOTE: intentionally does NOT use `Depends(SessionContextGuard(...).post)` here. That guard's
# own `request: RequestType | None` parameter re-parses the JSON body against the *entire* union
# of every method's request types, and an all-optional member earlier in that union (e.g.
# CreateSessionRequest) can trivially validate against any body and win before our actual typed
# request is tried — silently dropping fields like `problem_id`/`session_id` (hit and documented
# in this method's original single-problem version). `fetch_problem_with_role_check` gives the
# same access-control check directly, without that ambiguity.


def _get_problem_or_404(user: User, request_problem_id: int, db_session: Session):
    problem_db = fetch_problem_with_role_check(user, request_problem_id, db_session)
    if problem_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem {request_problem_id} not found.")
    return problem_db


def _get_context_or_503(problem_id: int) -> JinaScenarioContext:
    try:
        return get_context(problem_id)
    except JinaScenarioError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


def _build_meta(ctx: JinaScenarioContext) -> JinaProblemMeta:
    objectives = [
        JinaObjectiveMeta(
            symbol=sym,
            name=m.name,
            unit=m.unit,
            label=m.label,
            maximize=m.maximize,
            varies_by_scenario=sym in ctx.varying_obj_symbols,
        )
        for sym, m in ctx.obj_meta.items()
    ]
    strategic_vars = [
        JinaStrategicVarMeta(
            symbol=sym, name=m.name, label=m.label, component=m.component, unit=m.unit, axis_max=m.axis_max
        )
        for sym, m in ctx.strategic_meta.items()
    ]
    scalarizers = [JinaScalarizerMeta(name=s.name, emphasize=s.emphasize, label=s.label) for s in ctx.scalarizer_defs]

    return JinaProblemMeta(
        problem_id=ctx.problem_id,
        problem_name=ctx.problem.name,
        scenario_model_id=ctx.scenario_model_id,
        objectives=objectives,
        strategic_vars=strategic_vars,
        scalarizers=scalarizers,
        all_scenarios=ctx.all_scenarios,
        default_domain_thresholds=ctx.settings.default_domain_thresholds or {},
        default_af_absolute_floors=ctx.settings.default_af_absolute_floors or {},
        supports_compound_scenarios=bool(ctx.settings.compound_scenario_hook),
        compound_description=None,
    )


def _latest_state_db(db_session: Session, problem_id: int, session_id: int | None, kind: StateKind) -> StateDB | None:
    statement = (
        select(StateDB)
        .where(StateDB.problem_id == problem_id, StateDB.session_id == session_id)
        .order_by(StateDB.id.desc())
    )
    for state_db in db_session.exec(statement).all():
        if state_db.base_state is not None and state_db.base_state.kind == kind:
            return state_db
    return None


def _design_registry_from_state(state: DistrictHeatingRobustIterationState | None) -> dict[int, dict]:
    """Reconstruct the running design registry, converting stored signature lists back to tuples."""
    if state is None:
        return {}
    registry: dict[int, dict] = {}
    for design_id_str, stored in state.design_registry.items():
        entry = dict(stored)
        entry["signature"] = tuple(entry["signature"])
        registry[int(design_id_str)] = entry
    return registry


@router.post("/iterate")
def iterate(
    request: DistrictHeatingRobustIterateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingRobustIterateResponse:
    """Run one robust-solve iteration: every scalarizer variant, solved live via Gurobi.

    Slow (each solve takes real time even parallelized) — the frontend should show accurate
    loading-state copy, not a generic spinner.
    """
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    interactive_session = fetch_interactive_session(user, db_session, request)
    parent_state = fetch_parent_state(user, request, db_session, interactive_session=interactive_session)

    ctx = _get_context_or_503(problem_db.id)
    session_id = interactive_session.id if interactive_session is not None else None

    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_ROBUST_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_ROBUST_WISHLIST
    )

    design_registry = _design_registry_from_state(latest_iteration_db.state if latest_iteration_db else None)
    solution_number_map = (
        {int(k): v for k, v in latest_iteration_db.state.solution_number_map.items()} if latest_iteration_db else {}
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []
    iteration_number = (latest_iteration_db.state.iteration_number + 1) if latest_iteration_db else 1

    missing = [o for o in ctx.obj_symbols if o not in request.reference_point]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reference point is missing objective(s): {missing}. Must provide all of {ctx.obj_symbols}.",
        )
    g_robust = {
        ctx.robust_symbol_map[obj]: val for obj, val in request.reference_point.items() if obj in ctx.obj_symbols
    }

    solutions = run_iteration(
        ctx, g_robust, iteration_number, design_registry, solution_number_map, request.max_solutions
    )

    iteration_state = DistrictHeatingRobustIterationState(
        reference_point=request.reference_point,
        note=request.note,
        iteration_number=iteration_number,
        design_registry={str(k): {**v, "signature": list(v["signature"])} for k, v in design_registry.items()},
        solution_number_map={str(k): v for k, v in solution_number_map.items()},
        solutions=solutions,
    )

    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=session_id,
        parent_id=parent_state.id if parent_state is not None else None,
        state=iteration_state,
    )
    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return DistrictHeatingRobustIterateResponse(
        state_id=state.id,
        iteration_number=iteration_number,
        reference_point=request.reference_point,
        note=request.note,
        solutions=[DistrictHeatingRobustMatchedSolution.model_validate(s) for s in solutions],
        wish_list=wish_list,
        global_ideal=ctx.global_ideal_obj,
        global_nadir=ctx.global_nadir_obj,
        all_scenarios=ctx.all_scenarios,
        meta=_build_meta(ctx),
    )


@router.get("/get_or_initialize")
def get_or_initialize(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
) -> DistrictHeatingRobustIterateResponse:
    """Return the latest state for this session, or an empty starting point if none exists yet.

    The first call against a not-yet-cached problem is slow (builds and solves the payoff table
    for the robust problem, ~1 minute); subsequent calls reuse the cached context.
    """
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    effective_session_id = session_id if session_id is not None else user.active_session_id

    ctx = _get_context_or_503(problem_db.id)

    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ROBUST_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ROBUST_WISHLIST
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    if latest_iteration_db is None:
        return DistrictHeatingRobustIterateResponse(
            state_id=0,
            iteration_number=0,
            reference_point={},
            note=None,
            solutions=[],
            wish_list=wish_list,
            global_ideal=ctx.global_ideal_obj,
            global_nadir=ctx.global_nadir_obj,
            all_scenarios=ctx.all_scenarios,
            meta=_build_meta(ctx),
        )

    latest_iteration = latest_iteration_db.state
    return DistrictHeatingRobustIterateResponse(
        state_id=latest_iteration_db.id,
        iteration_number=latest_iteration.iteration_number,
        reference_point=latest_iteration.reference_point,
        note=latest_iteration.note,
        solutions=[DistrictHeatingRobustMatchedSolution.model_validate(s) for s in latest_iteration.solutions],
        wish_list=wish_list,
        global_ideal=ctx.global_ideal_obj,
        global_nadir=ctx.global_nadir_obj,
        all_scenarios=ctx.all_scenarios,
        meta=_build_meta(ctx),
    )


@router.post("/wishlist/add")
def wishlist_add(
    request: DistrictHeatingRobustWishlistUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingRobustWishlistResponse:
    """Add design ids to the running wish list. Only designs already shown in some iteration qualify."""
    return _wishlist_update(user, db_session, request, add=True)


@router.post("/wishlist/remove")
def wishlist_remove(
    request: DistrictHeatingRobustWishlistUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingRobustWishlistResponse:
    """Remove design ids from the running wish list. Removes all copies of a repeated id."""
    return _wishlist_update(user, db_session, request, add=False)


def _wishlist_update(
    user: User, db_session: Session, request: DistrictHeatingRobustWishlistUpdateRequest, *, add: bool
) -> DistrictHeatingRobustWishlistResponse:
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    interactive_session = fetch_interactive_session(user, db_session, request)
    parent_state = fetch_parent_state(user, request, db_session, interactive_session=interactive_session)
    session_id = interactive_session.id if interactive_session is not None else None

    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_ROBUST_WISHLIST
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    if add:
        latest_iteration_db = _latest_state_db(
            db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_ROBUST_ITERATE
        )
        all_seen_ids = {int(k) for k in latest_iteration_db.state.design_registry} if latest_iteration_db else set()

        skipped = [d for d in request.design_ids if d not in all_seen_ids]
        wish_list.extend(d for d in request.design_ids if d in all_seen_ids)
    else:
        current_ids = set(wish_list)
        skipped = sorted(set(request.design_ids) - current_ids)
        ids_to_remove = set(request.design_ids)
        wish_list = [d for d in wish_list if d not in ids_to_remove]

    wishlist_state = DistrictHeatingRobustWishlistState(wish_list=wish_list)
    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=session_id,
        parent_id=parent_state.id if parent_state is not None else None,
        state=wishlist_state,
    )
    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return DistrictHeatingRobustWishlistResponse(state_id=state.id, wish_list=wish_list, skipped_ids=skipped)


@router.get("/session_tree")
def session_tree(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
) -> list[DistrictHeatingRobustSessionTreeEntry]:
    """All iteration/wish-list-update states for a session, oldest first."""
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    effective_session_id = session_id if session_id is not None else user.active_session_id
    statement = (
        select(StateDB)
        .where(StateDB.problem_id == problem_db.id, StateDB.session_id == effective_session_id)
        .order_by(StateDB.id.asc())
    )
    entries: list[DistrictHeatingRobustSessionTreeEntry] = []
    for state_db in db_session.exec(statement).all():
        if state_db.base_state is None:
            continue
        kind = state_db.base_state.kind
        if kind == StateKind.DISTRICT_HEATING_ROBUST_ITERATE:
            sub = state_db.state
            entries.append(
                DistrictHeatingRobustSessionTreeEntry(
                    state_id=state_db.id,
                    kind="iterate",
                    parent_id=state_db.parent_id,
                    iteration_number=sub.iteration_number,
                    reference_point=sub.reference_point,
                    note=sub.note,
                    solutions=sub.solutions,
                )
            )
        elif kind == StateKind.DISTRICT_HEATING_ROBUST_WISHLIST:
            sub = state_db.state
            entries.append(
                DistrictHeatingRobustSessionTreeEntry(
                    state_id=state_db.id,
                    kind="wishlist_update",
                    parent_id=state_db.parent_id,
                    wish_list=sub.wish_list,
                )
            )
    return entries


@router.get("/strategic-designs")
def strategic_designs(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
) -> DistrictHeatingRobustStrategicDesignsResponse:
    """Every strategic design discovered this session.

    Variable values, discovering scalarizer, and worst-case robust objectives, for the DM to browse. Stateless read
    of the already-solved `design_registry` — no new Gurobi solve.
    """
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    effective_session_id = session_id if session_id is not None else user.active_session_id

    ctx = _get_context_or_503(problem_db.id)
    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ROBUST_ITERATE
    )
    design_registry = _design_registry_from_state(latest_iteration_db.state if latest_iteration_db else None)
    solution_number_map = (
        {int(k): v for k, v in latest_iteration_db.state.solution_number_map.items()} if latest_iteration_db else {}
    )

    return DistrictHeatingRobustStrategicDesignsResponse(
        designs=list_strategic_designs(ctx, design_registry, solution_number_map),
        axis_max=strategic_axis_max(ctx),
    )


@router.post("/analysis")
def analysis(
    request: DistrictHeatingRobustAnalysisRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingRobustAnalysisResponse:
    """Robustness + antifragility analysis for the current wish list.

    Stateless read, no `StateDB` write.
    """
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    effective_session_id = request.session_id if request.session_id is not None else user.active_session_id

    ctx = _get_context_or_503(problem_db.id)
    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ROBUST_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ROBUST_WISHLIST
    )

    design_registry = _design_registry_from_state(latest_iteration_db.state if latest_iteration_db else None)
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    result = compute_wish_list_analysis(
        ctx, design_registry, wish_list, request.domain_thresholds, request.af_absolute_floors
    )
    return DistrictHeatingRobustAnalysisResponse(**result)


@router.post("/combined-scenario-analysis")
def combined_scenario_analysis(
    request: DistrictHeatingRobustCombinedScenarioRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingRobustCombinedScenarioResponse:
    """Compound-disruption stress test.

    Re-evaluate candidate designs under every combined scenario the problem's configured hook produces (see
    `desdeo.api.routers.jina_compound`). Slow — solves live, no `StateDB` write.
    """
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    effective_session_id = request.session_id if request.session_id is not None else user.active_session_id

    ctx = _get_context_or_503(problem_db.id)
    if not ctx.settings.compound_scenario_hook:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="This problem does not define a compound-scenario hook.",
        )

    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ROBUST_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ROBUST_WISHLIST
    )

    design_registry = _design_registry_from_state(latest_iteration_db.state if latest_iteration_db else None)
    solution_number_map = (
        {int(k): v for k, v in latest_iteration_db.state.solution_number_map.items()} if latest_iteration_db else {}
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    if request.design_ids is not None:
        candidate_ids = sorted(set(request.design_ids))
    elif wish_list:
        candidate_ids = sorted(set(wish_list))
    else:
        candidate_ids = sorted(design_registry.keys())

    missing = [d for d in candidate_ids if d not in design_registry]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown design id(s): {missing}")

    # The ASF scalarizes exactly the objectives named in the reference point, so a partial one
    # would silently drop objectives from the re-evaluation rather than fail — rejected here.
    missing_objs = [s for s in ctx.obj_symbols if s not in request.reference_point]
    if missing_objs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"reference_point is missing objective(s) {missing_objs}; it must cover all of {ctx.obj_symbols}."),
        )
    reference_point = {s: float(request.reference_point[s]) for s in ctx.obj_symbols}

    if not candidate_ids:
        return DistrictHeatingRobustCombinedScenarioResponse(candidate_ids=[], combo_names=[], rows=[], summary=[])

    # Everything from here on solves live against DM-supplied scenario modules and an unbounded
    # design registry, so it can fail in ways that aren't `JinaScenarioError` — a KeyError for a
    # symbol the persisted problem and the freshly built scenarios disagree on, a solver error,
    # a missing entry in `robust_vals`. Those used to escape as a bare `Internal Server Error`
    # with the cause visible only in the server log, which is useless to a DM sitting in the UI.
    # `summarize_compound_results` is inside the guard too: it indexes `design_registry` and
    # `robust_vals` directly and used to sit outside it.
    try:
        hook = resolve_hook(ctx.settings.compound_scenario_hook)
        scenario_set = hook(ctx)
        rows = run_compound_analysis(ctx, scenario_set, design_registry, candidate_ids, reference_point)

        supports_superadditivity = False
        reference_rows: list[dict] = []
        if ctx.settings.compound_reference_hook and scenario_set.pair_components:
            reference_hook = resolve_hook(ctx.settings.compound_reference_hook)
            reference_set = reference_hook(ctx)
            # Same reference point as the combined rows: superadditivity is
            # `combined + baseline - A_alone - B_alone`, so re-evaluating the reference scenarios
            # against different aspirations would make that difference measure the change of
            # reference point as much as the interaction of the two disruptions.
            reference_rows = run_compound_analysis(ctx, reference_set, design_registry, candidate_ids, reference_point)
            compute_superadditivity(ctx.obj_symbols, rows, reference_rows, scenario_set.pair_components)
            supports_superadditivity = True

        summary = summarize_compound_results(ctx, rows, candidate_ids, design_registry, solution_number_map)
    except JinaScenarioError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except Exception as e:
        logger.exception("Compound-disruption stress test failed for problem %s", problem_db.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compound-disruption stress test failed: {type(e).__name__}: {e}",
        ) from e

    return DistrictHeatingRobustCombinedScenarioResponse(
        candidate_ids=candidate_ids,
        combo_names=scenario_set.names,
        rows=rows,
        summary=summary,
        supports_superadditivity=supports_superadditivity,
        reference_rows=reference_rows,
        pair_components=scenario_set.pair_components,
    )
