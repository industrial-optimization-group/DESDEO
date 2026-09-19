"""Endpoints for the JINA single-scenario pool-matching interactive method.

Generic: every endpoint takes a `problem_id` and works against whatever problem that id points
to, provided it has an attached `JinaPoolMetaData` row (see
`district_heating_system_data.get_pool_context` and `desdeo/api/db_init_district_heating.py` for
how the district heating problem — the first, no longer the only, problem this serves — got
registered that way).

Scenario-robust reference-point matching over a decision maker's pre-computed candidate pool
(ported from `the_DM_session.ipynb`). This method never touches `desdeo.problem.Problem` for
solving — only for objective/variable display metadata (names, units, bounds); it always matches
against a pre-computed CSV pool.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    DistrictHeatingAnalysisRequest,
    DistrictHeatingAnalysisResponse,
    DistrictHeatingIterateRequest,
    DistrictHeatingIterateResponse,
    DistrictHeatingIterationState,
    DistrictHeatingMatchedSolution,
    DistrictHeatingSessionTreeEntry,
    DistrictHeatingStrategicDesignsResponse,
    DistrictHeatingWishlistResponse,
    DistrictHeatingWishlistState,
    DistrictHeatingWishlistUpdateRequest,
    JinaObjectiveMeta,
    JinaProblemMeta,
    JinaScalarizerMeta,
    JinaStrategicVarMeta,
    StateDB,
    User,
)
from desdeo.api.models.generic_states import StateKind
from desdeo.api.routers.district_heating_system_data import (
    CandidatePool,
    DistrictHeatingDataError,
    JinaPoolContext,
    JinaPoolError,
    MatchedSolution,
    compute_wish_list_analysis,
    get_pool_context,
    list_strategic_designs,
    load_candidate_pool,
    run_iteration,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.routers.utils import fetch_interactive_session, fetch_parent_state, fetch_problem_with_role_check

router = APIRouter(prefix="/method/district-heating-system")

# NOTE: intentionally does NOT use `Depends(SessionContextGuard(...).post)` — same union-ambiguity
# reason documented in district_heating_robust.py.


def _get_problem_or_404(user: User, request_problem_id: int, db_session: Session):
    problem_db = fetch_problem_with_role_check(user, request_problem_id, db_session)
    if problem_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem {request_problem_id} not found.")
    return problem_db


def _get_context_or_503(problem_id: int) -> JinaPoolContext:
    try:
        return get_pool_context(problem_id)
    except JinaPoolError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


def _get_pool_or_503(ctx: JinaPoolContext) -> CandidatePool:
    try:
        return load_candidate_pool(ctx)
    except DistrictHeatingDataError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e


def _build_meta(ctx: JinaPoolContext, pool: CandidatePool, problem_name: str) -> JinaProblemMeta:
    objectives = [
        JinaObjectiveMeta(
            symbol=sym, name=m.name, unit=m.unit, label=m.label, maximize=m.maximize, varies_by_scenario=True
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
        problem_name=problem_name,
        scenario_model_id=None,
        objectives=objectives,
        strategic_vars=strategic_vars,
        scalarizers=scalarizers,
        all_scenarios=pool.all_scenarios,
        default_domain_thresholds=ctx.settings.default_domain_thresholds or {},
        default_af_absolute_floors=ctx.settings.default_af_absolute_floors or {},
        supports_compound_scenarios=False,
        compound_description=None,
        lambda_objective=ctx.lambda_objective,
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


def _matched_solutions_to_dicts(solutions: list[MatchedSolution]) -> list[dict]:
    return [
        {
            "design_id": m.design_id,
            "solution_number": m.solution_number,
            "matched_by": m.matched_by,
            "n_scenarios": m.n_scenarios,
            "rows": m.rows,
            "worst_case": m.worst_case,
            "best_case": m.best_case,
        }
        for m in solutions
    ]


@router.post("/iterate")
def iterate(
    request: DistrictHeatingIterateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingIterateResponse:
    """Run one round of scenario-robust reference-point matching.

    Ports `run_iteration` from `the_DM_session.ipynb` as-is: scores every not-yet-shown
    candidate design with every configured scalarizer and returns up to `max_solutions` new,
    never-before-shown designs.
    """
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    interactive_session = fetch_interactive_session(user, db_session, request)
    parent_state = fetch_parent_state(user, request, db_session, interactive_session=interactive_session)

    ctx = _get_context_or_503(problem_db.id)
    pool = _get_pool_or_503(ctx)
    session_id = interactive_session.id if interactive_session is not None else None

    latest_iteration_db = _latest_state_db(db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_ITERATE)
    latest_wishlist_db = _latest_state_db(db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_WISHLIST)

    already_shown_ids = set(latest_iteration_db.state.already_shown_ids) if latest_iteration_db else set()
    solution_number_map = (
        {int(k): v for k, v in latest_iteration_db.state.solution_number_map.items()} if latest_iteration_db else {}
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    try:
        matched = run_iteration(
            pool,
            request.reference_point,
            already_shown_ids,
            solution_number_map,
            ctx.obj_symbols,
            ctx.scalarizer_defs,
            request.max_solutions,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    iteration_state = DistrictHeatingIterationState(
        reference_point=request.reference_point,
        max_solutions=request.max_solutions,
        note=request.note,
        already_shown_ids=sorted(already_shown_ids),
        solution_number_map={str(k): v for k, v in solution_number_map.items()},
        solutions=_matched_solutions_to_dicts(matched),
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

    return DistrictHeatingIterateResponse(
        state_id=state.id,
        reference_point=request.reference_point,
        note=request.note,
        solutions=[DistrictHeatingMatchedSolution.model_validate(s) for s in iteration_state.solutions],
        wish_list=wish_list,
        already_shown_ids=sorted(already_shown_ids),
        global_ideal=pool.global_ideal,
        global_nadir=pool.global_nadir,
        all_scenarios=pool.all_scenarios,
        meta=_build_meta(ctx, pool, problem_db.name),
    )


@router.get("/get_or_initialize")
def get_or_initialize(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
) -> DistrictHeatingIterateResponse:
    """Return the latest state for this session, or an empty starting point if none exists yet."""
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    effective_session_id = session_id if session_id is not None else user.active_session_id

    ctx = _get_context_or_503(problem_db.id)
    pool = _get_pool_or_503(ctx)

    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_WISHLIST
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    if latest_iteration_db is None:
        return DistrictHeatingIterateResponse(
            state_id=0,
            reference_point={},
            note=None,
            solutions=[],
            wish_list=wish_list,
            already_shown_ids=[],
            global_ideal=pool.global_ideal,
            global_nadir=pool.global_nadir,
            all_scenarios=pool.all_scenarios,
            meta=_build_meta(ctx, pool, problem_db.name),
        )

    latest_iteration = latest_iteration_db.state
    return DistrictHeatingIterateResponse(
        state_id=latest_iteration_db.id,
        reference_point=latest_iteration.reference_point,
        note=latest_iteration.note,
        solutions=[DistrictHeatingMatchedSolution.model_validate(s) for s in latest_iteration.solutions],
        wish_list=wish_list,
        already_shown_ids=latest_iteration.already_shown_ids,
        global_ideal=pool.global_ideal,
        global_nadir=pool.global_nadir,
        all_scenarios=pool.all_scenarios,
        meta=_build_meta(ctx, pool, problem_db.name),
    )


@router.post("/wishlist/add")
def wishlist_add(
    request: DistrictHeatingWishlistUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingWishlistResponse:
    """Add design ids to the running wish list. Only designs already shown in some iteration qualify."""
    return _wishlist_update(user, db_session, request, add=True)


@router.post("/wishlist/remove")
def wishlist_remove(
    request: DistrictHeatingWishlistUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingWishlistResponse:
    """Remove design ids from the running wish list. Removes all copies of a repeated id."""
    return _wishlist_update(user, db_session, request, add=False)


def _wishlist_update(
    user: User, db_session: Session, request: DistrictHeatingWishlistUpdateRequest, *, add: bool
) -> DistrictHeatingWishlistResponse:
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    interactive_session = fetch_interactive_session(user, db_session, request)
    parent_state = fetch_parent_state(user, request, db_session, interactive_session=interactive_session)
    session_id = interactive_session.id if interactive_session is not None else None

    latest_wishlist_db = _latest_state_db(db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_WISHLIST)
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    if add:
        latest_iteration_db = _latest_state_db(
            db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_ITERATE
        )
        all_seen_ids = set(latest_iteration_db.state.already_shown_ids) if latest_iteration_db else set()

        skipped = [d for d in request.design_ids if d not in all_seen_ids]
        wish_list.extend(d for d in request.design_ids if d in all_seen_ids)
    else:
        current_ids = set(wish_list)
        skipped = sorted(set(request.design_ids) - current_ids)
        ids_to_remove = set(request.design_ids)
        wish_list = [d for d in wish_list if d not in ids_to_remove]

    wishlist_state = DistrictHeatingWishlistState(wish_list=wish_list)
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

    return DistrictHeatingWishlistResponse(state_id=state.id, wish_list=wish_list, skipped_ids=skipped)


@router.get("/session_tree")
def session_tree(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
) -> list[DistrictHeatingSessionTreeEntry]:
    """All iteration/wish-list-update states for a session, oldest first."""
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    effective_session_id = session_id if session_id is not None else user.active_session_id
    statement = (
        select(StateDB)
        .where(StateDB.problem_id == problem_db.id, StateDB.session_id == effective_session_id)
        .order_by(StateDB.id.asc())
    )
    entries: list[DistrictHeatingSessionTreeEntry] = []
    for state_db in db_session.exec(statement).all():
        if state_db.base_state is None:
            continue
        kind = state_db.base_state.kind
        if kind == StateKind.DISTRICT_HEATING_ITERATE:
            sub = state_db.state
            entries.append(
                DistrictHeatingSessionTreeEntry(
                    state_id=state_db.id,
                    kind="iterate",
                    parent_id=state_db.parent_id,
                    reference_point=sub.reference_point,
                    note=sub.note,
                    solutions=sub.solutions,
                )
            )
        elif kind == StateKind.DISTRICT_HEATING_WISHLIST:
            sub = state_db.state
            entries.append(
                DistrictHeatingSessionTreeEntry(
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
) -> DistrictHeatingStrategicDesignsResponse:
    """Every design in the candidate pool.

    Capacities, originating scenario, and full performance breakdown, for the DM to browse. Ports
    `Vis_strategic_decisions.ipynb`. Stateless read of the whole pool — unlike the sibling multi-scenario method,
    this isn't scoped to a session, since the pool itself isn't session-scoped either (it's precomputed once, not
    discovered incrementally).
    """
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    ctx = _get_context_or_503(problem_db.id)
    pool = _get_pool_or_503(ctx)
    return DistrictHeatingStrategicDesignsResponse(
        designs=list_strategic_designs(pool, ctx.strategic_symbols, ctx.obj_symbols),
        axis_max={sym: m.axis_max for sym, m in ctx.strategic_meta.items()},
    )


@router.post("/analysis")
def analysis(
    request: DistrictHeatingAnalysisRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingAnalysisResponse:
    """Robustness + antifragility analysis for the current wish list.

    Ports `stage_2c_analysis.ipynb`: max regret and antifragility are computed over the
    full candidate pool (stable normalization), domain criterion over the wish list only.
    `domain_thresholds`/`af_absolute_floors` are DM-supplied (the notebook has the DM hand-edit
    these as constants). A read-only computation, no `StateDB` write.
    """
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    effective_session_id = request.session_id if request.session_id is not None else user.active_session_id

    ctx = _get_context_or_503(problem_db.id)
    pool = _get_pool_or_503(ctx)
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_WISHLIST
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    result = compute_wish_list_analysis(
        pool, wish_list, ctx.obj_symbols, request.domain_thresholds, request.af_absolute_floors
    )
    return DistrictHeatingAnalysisResponse(**result)
