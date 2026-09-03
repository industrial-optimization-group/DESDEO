"""Endpoints for the JINA combined multi-scenario interactive method.

Generic in the same way as `district_heating_robust`: every endpoint takes a `problem_id` and
works against whatever problem that id points to, provided it has an attached scenario model.
The two methods share the problem, the scenario model and the `JinaMultiScenarioMetaData`
settings row — they differ only in what the decision maker expresses a preference over.

- `district-heating-robust` aggregates each objective to its worst case across scenarios and
  takes one aspiration level per objective.
- this method drops that aggregation and takes one aspiration level per (objective, scenario)
  cell, so a target can differ between scenarios.

Solves live on every iteration and persists each round as a `StateDB` row, so the wish list and
the iteration history survive a reload — same session/state machinery as the multi-scenario
method, under its own `StateKind`s because the reference point lives in a different key space.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    DistrictHeatingCombinedIterationState,
    DistrictHeatingCombinedWishlistState,
    StateDB,
    User,
)
from desdeo.api.models.district_heating_combined import (
    DistrictHeatingCombinedAnalysisRequest,
    DistrictHeatingCombinedAnalysisResponse,
    DistrictHeatingCombinedCell,
    DistrictHeatingCombinedCellResult,
    DistrictHeatingCombinedInitializeRequest,
    DistrictHeatingCombinedInitializeResponse,
    DistrictHeatingCombinedIterateRequest,
    DistrictHeatingCombinedIterateResponse,
    DistrictHeatingCombinedSessionTreeEntry,
    DistrictHeatingCombinedSessionTreeResponse,
    DistrictHeatingCombinedSolution,
    DistrictHeatingCombinedWishlistResponse,
    DistrictHeatingCombinedWishlistUpdateRequest,
)
from desdeo.api.models.generic_states import StateKind
from desdeo.api.routers.district_heating_combined_data import (
    CombinedContext,
    compute_combined_analysis,
    design_signature,
    get_combined_context,
    run_combined_iteration,
    scenario_breakdown,
)
from desdeo.api.routers.district_heating_robust_data import JinaScenarioError
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.routers.utils import fetch_interactive_session, fetch_problem_with_role_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/method/district-heating-combined")


def _get_problem_or_404(user: User, request_problem_id: int, db_session: Session):
    problem_db = fetch_problem_with_role_check(user, request_problem_id, db_session)
    if problem_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Problem {request_problem_id} not found.")
    return problem_db


def _get_context_or_422(problem_id: int) -> CombinedContext:
    try:
        return get_combined_context(problem_id)
    except JinaScenarioError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Building the combined multi-scenario context failed for problem %s", problem_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not build the combined scenario problem: {type(e).__name__}: {e}",
        ) from e


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


def _design_registry_from_state(state: DistrictHeatingCombinedIterationState | None) -> dict[int, dict]:
    """Registry entries round-trip through JSON, so `signature` comes back as a list. Convert it
    back to a tuple here, once, rather than at every comparison site.
    """
    if state is None:
        return {}
    return {
        int(design_id): {**entry, "signature": tuple(entry["signature"])}
        for design_id, entry in (state.design_registry or {}).items()
    }


def _solution_from_state(state: DistrictHeatingCombinedIterationState) -> DistrictHeatingCombinedSolution | None:
    if not state.cell_results:
        return None
    return DistrictHeatingCombinedSolution(
        design_id=state.design_id,
        solution_number=state.solution_number,
        repeat=state.repeat,
        alpha=state.alpha,
        all_reached=state.all_reached,
        cell_results=[DistrictHeatingCombinedCellResult.model_validate(r) for r in state.cell_results],
        strategic_values=state.strategic_values,
        breakdown=state.breakdown,
    )


def _grid_fields(cctx: CombinedContext) -> dict:
    base = cctx.base
    return {
        "scenarios": list(base.all_scenarios),
        "objectives": list(base.obj_symbols),
        "objective_labels": {sym: meta.label for sym, meta in base.obj_meta.items()},
        "default_domain_thresholds": base.settings.default_domain_thresholds or {},
    }


@router.post("/initialize")
def initialize(
    request: DistrictHeatingCombinedInitializeRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingCombinedInitializeResponse:
    """The (objective, scenario) grid the decision maker fills in, with each cell's attainable
    span.

    Slow on the first call for a problem — it runs one payoff table per scenario to get those
    spans — and cached per problem afterwards.
    """
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    cctx = _get_context_or_422(problem_db.id)
    base = cctx.base

    return DistrictHeatingCombinedInitializeResponse(
        problem_id=problem_db.id,
        problem_name=problem_db.name,
        scenarios=list(base.all_scenarios),
        objectives=list(base.obj_symbols),
        objective_labels={sym: meta.label for sym, meta in base.obj_meta.items()},
        strategic_symbols=list(base.strategic_symbols),
        strategic_labels={sym: meta.label for sym, meta in base.strategic_meta.items()},
        strategic_units={sym: meta.unit for sym, meta in base.strategic_meta.items() if meta.unit is not None},
        cells=[
            DistrictHeatingCombinedCell(
                symbol=c.symbol,
                obj_symbol=c.obj_symbol,
                scenario=c.scenario,
                shared=c.shared,
                label=c.label,
                unit=c.unit,
                maximize=c.maximize,
                ideal=c.ideal,
                nadir=c.nadir,
                weight=c.weight,
            )
            for c in cctx.cells
        ],
    )


@router.get("/get_or_initialize")
def get_or_initialize(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
) -> DistrictHeatingCombinedIterateResponse:
    """The latest iteration for a session, or an empty state before the first one.

    Lets the page resume a session — wish list, last reference point, last solution — without
    re-solving anything.
    """
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    cctx = _get_context_or_422(problem_db.id)
    effective_session_id = session_id if session_id is not None else user.active_session_id

    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_COMBINED_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_COMBINED_WISHLIST
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    if latest_iteration_db is None:
        return DistrictHeatingCombinedIterateResponse(
            state_id=0, iteration_number=0, wish_list=wish_list, **_grid_fields(cctx)
        )

    state = latest_iteration_db.state
    return DistrictHeatingCombinedIterateResponse(
        state_id=latest_iteration_db.id,
        iteration_number=state.iteration_number,
        reference_point=state.reference_point,
        note=state.note,
        solution=_solution_from_state(state),
        wish_list=wish_list,
        **_grid_fields(cctx),
    )


@router.post("/iterate")
def iterate(
    request: DistrictHeatingCombinedIterateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingCombinedIterateResponse:
    """One ASF solve against the decision maker's per-cell aspiration levels."""
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    interactive_session = fetch_interactive_session(user, db_session, request)
    session_id = interactive_session.id if interactive_session is not None else None
    cctx = _get_context_or_422(problem_db.id)

    # The ASF scalarizes exactly the objectives named in the reference point, so an incomplete one
    # would quietly leave cells out of the solve instead of failing.
    missing = [c.symbol for c in cctx.cells if c.symbol not in request.reference_point]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"reference_point is missing {len(missing)} cell(s): {missing[:5]}"
                f"{'...' if len(missing) > 5 else ''}. It must cover every cell from /initialize."
            ),
        )
    unknown = [sym for sym in request.reference_point if sym not in cctx.cells_by_symbol]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"reference_point has unknown symbol(s): {unknown[:5]}{'...' if len(unknown) > 5 else ''}.",
        )

    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_COMBINED_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_COMBINED_WISHLIST
    )
    design_registry = _design_registry_from_state(latest_iteration_db.state if latest_iteration_db else None)
    solution_number_map = (
        {int(k): v for k, v in latest_iteration_db.state.solution_number_map.items()} if latest_iteration_db else {}
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []
    iteration_number = (latest_iteration_db.state.iteration_number + 1) if latest_iteration_db else 1

    try:
        result = run_combined_iteration(cctx, request.reference_point)
    except JinaScenarioError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        logger.exception("Combined multi-scenario iteration failed for problem %s", problem_db.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Iteration failed: {type(e).__name__}: {e}",
        ) from e

    breakdown = scenario_breakdown(cctx, result.objective_values)

    # Two rounds that land on the same physical build are the same design: it keeps its original
    # id and solution number and is flagged as a repeat, rather than being counted twice in the
    # wish list or the domain criterion.
    signature = design_signature(cctx, result.strategic_values)
    existing_id = next((did for did, entry in design_registry.items() if tuple(entry["signature"]) == signature), None)
    repeat = existing_id is not None
    if existing_id is None:
        design_id = (max(design_registry) + 1) if design_registry else 1
        solution_number = (max(solution_number_map.values()) + 1) if solution_number_map else 1
        solution_number_map[design_id] = solution_number
    else:
        design_id = existing_id
        solution_number = solution_number_map.get(design_id, design_id)

    design_registry[design_id] = {
        "signature": list(signature),
        "first_iteration": design_registry.get(design_id, {}).get("first_iteration", iteration_number),
        "strategic_vals": result.strategic_values,
        "breakdown": breakdown,
        "objective_values": result.objective_values,
    }

    cell_result_dicts = [
        {
            "symbol": r.symbol,
            "aspiration": r.aspiration,
            "achieved": r.achieved,
            "scaled": r.scaled,
            "binds": r.binds,
        }
        for r in result.cell_results
    ]

    iteration_state = DistrictHeatingCombinedIterationState(
        reference_point=request.reference_point,
        note=request.note,
        iteration_number=iteration_number,
        design_registry={str(k): {**v, "signature": list(v["signature"])} for k, v in design_registry.items()},
        solution_number_map={str(k): v for k, v in solution_number_map.items()},
        alpha=result.alpha,
        all_reached=result.all_reached,
        design_id=design_id,
        solution_number=solution_number,
        repeat=repeat,
        cell_results=cell_result_dicts,
        strategic_values=result.strategic_values,
        breakdown=breakdown,
    )
    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=session_id,
        parent_id=latest_iteration_db.id if latest_iteration_db is not None else None,
        state=iteration_state,
    )
    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return DistrictHeatingCombinedIterateResponse(
        state_id=state.id,
        iteration_number=iteration_number,
        reference_point=request.reference_point,
        note=request.note,
        solution=DistrictHeatingCombinedSolution(
            design_id=design_id,
            solution_number=solution_number,
            repeat=repeat,
            alpha=result.alpha,
            all_reached=result.all_reached,
            cell_results=[DistrictHeatingCombinedCellResult.model_validate(r) for r in cell_result_dicts],
            strategic_values=result.strategic_values,
            breakdown=breakdown,
        ),
        wish_list=wish_list,
        **_grid_fields(cctx),
    )


@router.get("/session_tree")
def session_tree(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
) -> DistrictHeatingCombinedSessionTreeResponse:
    """Every iteration in a session, oldest first, so past rounds can be browsed without
    re-solving."""
    problem_db = _get_problem_or_404(user, problem_id, db_session)
    effective_session_id = session_id if session_id is not None else user.active_session_id

    statement = (
        select(StateDB)
        .where(StateDB.problem_id == problem_db.id, StateDB.session_id == effective_session_id)
        .order_by(StateDB.id.asc())
    )
    entries = []
    for state_db in db_session.exec(statement).all():
        if state_db.base_state is None or state_db.base_state.kind != StateKind.DISTRICT_HEATING_COMBINED_ITERATE:
            continue
        state = state_db.state
        entries.append(
            DistrictHeatingCombinedSessionTreeEntry(
                state_id=state_db.id,
                iteration_number=state.iteration_number,
                note=state.note,
                reference_point=state.reference_point,
                solution=_solution_from_state(state),
            )
        )
    return DistrictHeatingCombinedSessionTreeResponse(entries=entries)


@router.post("/wishlist/add")
def wishlist_add(
    request: DistrictHeatingCombinedWishlistUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingCombinedWishlistResponse:
    """Add design ids to the running wish list. Only designs already seen in some iteration
    qualify."""
    return _wishlist_update(user, db_session, request, add=True)


@router.post("/wishlist/remove")
def wishlist_remove(
    request: DistrictHeatingCombinedWishlistUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingCombinedWishlistResponse:
    """Remove design ids from the running wish list."""
    return _wishlist_update(user, db_session, request, add=False)


def _wishlist_update(
    user: User, db_session: Session, request: DistrictHeatingCombinedWishlistUpdateRequest, *, add: bool
) -> DistrictHeatingCombinedWishlistResponse:
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    interactive_session = fetch_interactive_session(user, db_session, request)
    session_id = interactive_session.id if interactive_session is not None else None

    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_COMBINED_WISHLIST
    )
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    if add:
        latest_iteration_db = _latest_state_db(
            db_session, problem_db.id, session_id, StateKind.DISTRICT_HEATING_COMBINED_ITERATE
        )
        seen_ids = {int(k) for k in latest_iteration_db.state.design_registry} if latest_iteration_db else set()
        # De-duplicated rather than appended blindly: a design that resurfaces in a later round
        # keeps its id, so adding it twice would double-count it in the domain criterion.
        for design_id in request.design_ids:
            if design_id in seen_ids and design_id not in wish_list:
                wish_list.append(design_id)
    else:
        ids_to_remove = set(request.design_ids)
        wish_list = [d for d in wish_list if d not in ids_to_remove]

    wishlist_state = DistrictHeatingCombinedWishlistState(wish_list=wish_list)
    state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=session_id,
        parent_id=latest_wishlist_db.id if latest_wishlist_db is not None else None,
        state=wishlist_state,
    )
    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    return DistrictHeatingCombinedWishlistResponse(state_id=state.id, wish_list=wish_list)


@router.post("/analysis")
def analysis(
    request: DistrictHeatingCombinedAnalysisRequest,
    user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_session)],
) -> DistrictHeatingCombinedAnalysisResponse:
    """Domain criterion over the wish-listed designs: how many scenarios each design meets each
    objective's threshold in.
    """
    problem_db = _get_problem_or_404(user, request.problem_id, db_session)
    cctx = _get_context_or_422(problem_db.id)
    effective_session_id = request.session_id if request.session_id is not None else user.active_session_id

    latest_iteration_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_COMBINED_ITERATE
    )
    latest_wishlist_db = _latest_state_db(
        db_session, problem_db.id, effective_session_id, StateKind.DISTRICT_HEATING_COMBINED_WISHLIST
    )
    design_registry = _design_registry_from_state(latest_iteration_db.state if latest_iteration_db else None)
    wish_list = list(latest_wishlist_db.state.wish_list) if latest_wishlist_db else []

    try:
        result = compute_combined_analysis(cctx, design_registry, wish_list, request.domain_thresholds)
    except Exception as e:
        logger.exception("Combined multi-scenario analysis failed for problem %s", problem_db.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {type(e).__name__}: {e}",
        ) from e

    return DistrictHeatingCombinedAnalysisResponse(**result)
