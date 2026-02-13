"""Defines end-points to access functionalities related to the E-NAUTILUS method."""

from typing import Annotated

import numpy as np
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ENautilusDecisionEventResponse,
    ENautilusFinalizeRequest,
    ENautilusFinalizeResponse,
    ENautilusFinalState,
    ENautilusRepresentativeSolutionsResponse,
    ENautilusSessionTreeResponse,
    ENautilusState,
    ENautilusStateResponse,
    ENautilusStepRequest,
    ENautilusStepResponse,
    ENautilusTreeNodeResponse,
    ProblemDB,
    RepresentativeNonDominatedSolutions,
    StateDB,
)
from desdeo.api.models.generic_states import State, StateKind
from desdeo.mcdm import ENautilusResult, enautilus_get_representative_solutions, enautilus_step
from desdeo.problem import Problem

from .utils import ContextField, SessionContext, SessionContextGuard

router = APIRouter(prefix="/method/enautilus")


@router.post("/step")
def step(
    request: ENautilusStepRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]))],
) -> ENautilusStepResponse:
    """Steps the E-NAUTILUS method."""
    db_session = context.db_session
    problem_db = context.problem_db
    problem = Problem.from_problemdb(problem_db)

    interactive_session = context.interactive_session
    parent_state = context.parent_state

    representative_solutions = db_session.exec(
        select(RepresentativeNonDominatedSolutions).where(
            RepresentativeNonDominatedSolutions.id == request.representative_solutions_id
        )
    ).first()

    if representative_solutions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Could not find the requested representative solutions for the problem with "
                f"id={request.representative_solutions_id}."
            ),
        )

    if request.current_iteration == 0:
        # First iteration, nadir as 'selected_point' and all points are reachable
        # Nadir point is expected in 'True' values, hence the multiplication by -1 for maximized objectives
        selected_point = {
            f"{obj.symbol}": (-1 if obj.maximize else 1)
            * np.max(representative_solutions.solution_data[f"{obj.symbol}_min"])
            for obj in problem.objectives
        }
        reachable_point_indices = list(range(len(representative_solutions.solution_data[problem.objectives[0].symbol])))
    else:
        # Not first iteration
        selected_point = request.selected_point
        reachable_point_indices = request.reachable_point_indices

    # iterate E-NAUTILUS
    results: ENautilusResult = enautilus_step(
        problem=problem,
        non_dominated_points=representative_solutions.solution_data,
        current_iteration=request.current_iteration,
        iterations_left=request.iterations_left,
        selected_point=selected_point,
        number_of_intermediate_points=request.number_of_intermediate_points,
        reachable_point_indices=reachable_point_indices,
    )

    enautilus_state = ENautilusState(
        non_dominated_solutions_id=request.representative_solutions_id,
        current_iteration=request.current_iteration,
        iterations_left=request.iterations_left,
        selected_point=selected_point,
        reachable_point_indices=reachable_point_indices,
        number_of_intermediate_points=request.number_of_intermediate_points,
        enautilus_results=results,
    )

    # create DB state and add it to the DB
    state_db = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=enautilus_state,
    )

    db_session.add(state_db)
    db_session.commit()
    db_session.refresh(state_db)

    return ENautilusStepResponse(
        state_id=state_db.id,
        current_iteration=results.current_iteration,
        iterations_left=results.iterations_left,
        intermediate_points=results.intermediate_points,
        reachable_best_bounds=results.reachable_best_bounds,
        reachable_worst_bounds=results.reachable_worst_bounds,
        closeness_measures=results.closeness_measures,
        reachable_point_indices=results.reachable_point_indices,
    )


@router.get("/get_state/{state_id}")
def get_state(
    state_id: int,
    db_session: Annotated[Session, Depends(get_session)],
) -> ENautilusStateResponse:
    """Fetch a previous state of the the E-NAUTILUS method."""
    state_db: StateDB | None = db_session.exec(select(StateDB).where(StateDB.id == state_id)).first()

    if state_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find 'StateDB' with id={state_id}"
        )

    if not isinstance(state_db.state, ENautilusState):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="The requested state does not contain an ENautilusState."
        )

    enautilus_state: ENautilusState = state_db.state
    results: ENautilusResult = enautilus_state.enautilus_results

    request = ENautilusStepRequest(
        problem_id=state_db.problem_id,
        session_id=state_db.session_id,
        parent_state_id=state_db.parent_id,
        representative_solutions_id=enautilus_state.non_dominated_solutions_id,
        current_iteration=enautilus_state.current_iteration,
        iterations_left=enautilus_state.iterations_left,
        selected_point=enautilus_state.selected_point,
        reachable_point_indices=enautilus_state.reachable_point_indices,
        number_of_intermediate_points=enautilus_state.number_of_intermediate_points,
    )

    response = ENautilusStepResponse(
        state_id=state_db.id,
        current_iteration=results.current_iteration,
        iterations_left=results.iterations_left,
        intermediate_points=results.intermediate_points,
        reachable_best_bounds=results.reachable_best_bounds,
        reachable_worst_bounds=results.reachable_worst_bounds,
        closeness_measures=results.closeness_measures,
        reachable_point_indices=results.reachable_point_indices,
    )

    return ENautilusStateResponse(request=request, response=response)


@router.get("/get_representative/{state_id}")
def get_representative(
    state_id: int, db_session: Annotated[Session, Depends(get_session)]
) -> ENautilusRepresentativeSolutionsResponse:
    """Computes the representative solutions that are closest to the intermediate solutions computed by E-NAUTILUS.

    This endpoint should be used to get the actual solution from the
    non-dominated representation used in the E-NAUTILUS method's last iteration
    (when number of iterations left is 0).

    Args:
        state_id (int): id of the `StateDB` with information on the intermediate
            points for which the representative solutions should be computed.
        db_session (Annotated[Session, Depends): the database session.

    Raises:
        HTTPException: 404 if a `StateDB`, `ProblemDB`, or
            `RepresentativeNonDominatedSolutions` instance cannot be found.
        HTTPException: 406 if the substate of the references `StateDB` is not an
            instance of `ENautilusState`.

    Returns:
        ENautilusRepresentativeSolutionsResponse: the information on the representative solutions.
    """
    state_db: StateDB | None = db_session.exec(select(StateDB).where(StateDB.id == state_id)).first()

    if state_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find 'StateDB' with id={state_id}"
        )

    if not isinstance(state_db.state, ENautilusState):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="The requested state does not contain an ENautilusState."
        )

    enautilus_state: ENautilusState = state_db.state
    enautilus_result: ENautilusResult = enautilus_state.enautilus_results

    non_dom_solutions_db = db_session.exec(
        select(RepresentativeNonDominatedSolutions).where(
            RepresentativeNonDominatedSolutions.id == enautilus_state.non_dominated_solutions_id
        )
    ).first()

    if non_dom_solutions_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Could not find 'RepresentativeNonDominatedSolutions' with "
                f"id={enautilus_state.non_dominated_solutions_id}"
            ),
        )

    non_dom_solutions = pl.DataFrame(non_dom_solutions_db.solution_data)

    problem_db = db_session.exec(select(ProblemDB).where(ProblemDB.id == state_db.problem_id)).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find 'ProblemDB' with id={state_db.problem_id}"
        )

    problem = Problem.from_problemdb(problem_db)

    representative_solutions = enautilus_get_representative_solutions(problem, enautilus_result, non_dom_solutions)

    return ENautilusRepresentativeSolutionsResponse(solutions=representative_solutions)


@router.post("/finalize")
def finalize_enautilus(
    request: ENautilusFinalizeRequest,
    context: Annotated[
        SessionContext,
        Depends(SessionContextGuard(require=[ContextField.PROBLEM, ContextField.PARENT_STATE])),
    ],
) -> ENautilusFinalizeResponse:
    """Finalize E-NAUTILUS by selecting the final solution.

    The parent state must be an E-NAUTILUS step with iterations_left == 0.
    The selected intermediate point is projected to the nearest point on the
    representative Pareto front using `enautilus_get_representative_solutions`.

    Note: The returned solution is the nearest point on the REPRESENTATIVE set,
    not necessarily a true Pareto optimal solution. A dominating solution may
    exist but would require additional optimization to find.

    Args:
        request: The finalization request with parent_state_id and selected_point_index.
        context: The session context.

    Returns:
        ENautilusFinalizeResponse with the final state ID and solution.

    Raises:
        HTTPException: 400 if parent state is not valid or iterations_left != 0.
        HTTPException: 404 if referenced states/solutions not found.
    """
    db_session = context.db_session
    parent_state = context.parent_state
    problem_db = context.problem_db
    interactive_session = context.interactive_session

    # Validate parent state exists and is E-NAUTILUS step
    if parent_state is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parent_state_id is required for finalization.",
        )

    if not isinstance(parent_state.state, ENautilusState):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent state must be an E-NAUTILUS step state.",
        )

    enautilus_state: ENautilusState = parent_state.state
    result: ENautilusResult = enautilus_state.enautilus_results

    # Validate iterations_left == 0
    if result.iterations_left != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize: iterations_left={result.iterations_left}, must be 0.",
        )

    # Validate selected_point_index
    if request.selected_point_index < 0 or request.selected_point_index >= len(result.intermediate_points):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid selected_point_index: {request.selected_point_index}. "
                f"Must be in range [0, {len(result.intermediate_points) - 1}]."
            ),
        )

    # Get the selected intermediate point
    selected_intermediate_point = result.intermediate_points[request.selected_point_index]

    # Get non-dominated solutions for projection
    non_dom_solutions_db = db_session.exec(
        select(RepresentativeNonDominatedSolutions).where(
            RepresentativeNonDominatedSolutions.id == enautilus_state.non_dominated_solutions_id
        )
    ).first()

    if non_dom_solutions_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Could not find 'RepresentativeNonDominatedSolutions' with "
                f"id={enautilus_state.non_dominated_solutions_id}"
            ),
        )

    non_dom_solutions = pl.DataFrame(non_dom_solutions_db.solution_data)

    # Get representative solutions (project to Pareto front)
    problem = Problem.from_problemdb(problem_db)
    representative_solutions = enautilus_get_representative_solutions(problem, result, non_dom_solutions)

    # Get the solution corresponding to the selected point
    final_solution = representative_solutions[request.selected_point_index]

    # Create final state
    final_state = ENautilusFinalState(
        origin_step_state_id=parent_state.id,
        selected_point_index=request.selected_point_index,
        selected_intermediate_point=selected_intermediate_point,
        solver_results=final_solution,
    )

    state_db = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session else None,
        parent_id=parent_state.id,
        state=final_state,
    )

    db_session.add(state_db)
    db_session.commit()
    db_session.refresh(state_db)

    return ENautilusFinalizeResponse(
        state_id=state_db.id,
        selected_intermediate_point=selected_intermediate_point,
        final_solution=final_solution,
    )


@router.get("/session_tree/{session_id}")
def get_session_tree(
    session_id: int, context: Annotated[SessionContext, Depends(SessionContextGuard())]
) -> ENautilusSessionTreeResponse:
    """Extract the full E-NAUTILUS decision tree for a session.

    Returns all step and final nodes, edges, root IDs, and pre-computed
    decision events capturing what the DM chose at each transition.

    Args:
        session_id: The interactive session ID.
        context: The context of the query.

    Returns:
        ENautilusSessionTreeResponse with nodes, edges, root_ids, and decision_events.
    """
    db_session = context.db_session

    # Query step states
    step_stmt = (
        select(StateDB)
        .join(State, StateDB.state_id == State.id)
        .where(StateDB.session_id == session_id)
        .where(State.kind == StateKind.ENAUTILUS_STEP)
        .order_by(StateDB.id)
    )
    step_state_dbs: list[StateDB] = list(db_session.exec(step_stmt).all())

    # Query final states
    final_stmt = (
        select(StateDB)
        .join(State, StateDB.state_id == State.id)
        .where(StateDB.session_id == session_id)
        .where(State.kind == StateKind.ENAUTILUS_FINAL)
        .order_by(StateDB.id)
    )
    final_state_dbs: list[StateDB] = list(db_session.exec(final_stmt).all())

    all_state_dbs = step_state_dbs + final_state_dbs
    all_node_ids = {sdb.id for sdb in all_state_dbs}

    # Compute depths
    parent_map = {sdb.id: sdb.parent_id for sdb in all_state_dbs}
    depths: dict[int, int] = {}
    for node_id in all_node_ids:
        depth = 0
        current = node_id
        while parent_map.get(current) is not None:
            parent = parent_map[current]
            if parent in all_node_ids:
                depth += 1
            current = parent
        depths[node_id] = depth

    nodes: list[ENautilusTreeNodeResponse] = []
    edges: list[list[int]] = []
    root_ids: list[int] = []
    # Map node_id -> parsed step data for decision event building
    step_data: dict[int, dict] = {}

    # Process step states
    for state_db in step_state_dbs:
        enautilus_state: ENautilusState = state_db.state
        if enautilus_state is None:
            continue

        result = enautilus_state.enautilus_results

        node = ENautilusTreeNodeResponse(
            node_id=state_db.id,
            parent_node_id=state_db.parent_id,
            depth=depths.get(state_db.id, 0),
            node_type="step",
            current_iteration=result.current_iteration,
            iterations_left=result.iterations_left,
            selected_point=enautilus_state.selected_point,
            intermediate_points=result.intermediate_points,
            closeness_measures=result.closeness_measures,
        )
        nodes.append(node)

        step_data[state_db.id] = {
            "current_iteration": result.current_iteration,
            "iterations_left": result.iterations_left,
            "selected_point": enautilus_state.selected_point,
            "intermediate_points": result.intermediate_points,
        }

        if state_db.parent_id is None:
            root_ids.append(state_db.id)
        elif state_db.parent_id in all_node_ids:
            edges.append([state_db.parent_id, state_db.id])

    # Process final states
    for state_db in final_state_dbs:
        final_state: ENautilusFinalState = state_db.state
        if final_state is None:
            continue

        final_obj = None
        if final_state.solver_results and final_state.solver_results.optimal_objectives:
            final_obj = final_state.solver_results.optimal_objectives

        node = ENautilusTreeNodeResponse(
            node_id=state_db.id,
            parent_node_id=state_db.parent_id,
            depth=depths.get(state_db.id, 0),
            node_type="final",
            selected_point_index=final_state.selected_point_index,
            selected_intermediate_point=final_state.selected_intermediate_point,
            final_solution_objectives=final_obj,
        )
        nodes.append(node)

        if state_db.parent_id in all_node_ids:
            edges.append([state_db.parent_id, state_db.id])

    # Build decision events for step-to-step edges
    decision_events: list[ENautilusDecisionEventResponse] = []
    for parent_id, child_id in edges:
        parent_data = step_data.get(parent_id)
        child_data = step_data.get(child_id)
        if parent_data is None or child_data is None:
            continue

        # Match chosen point to parent's intermediate points
        chosen_idx = _match_chosen_point(child_data["selected_point"], parent_data["intermediate_points"])

        event = ENautilusDecisionEventResponse(
            parent_node_id=parent_id,
            child_node_id=child_id,
            parent_iteration=parent_data["current_iteration"],
            child_iteration=child_data["current_iteration"],
            iterations_left_after=child_data["iterations_left"],
            starting_point=parent_data["selected_point"],
            chosen_point=child_data["selected_point"],
            chosen_option_idx=chosen_idx,
        )
        decision_events.append(event)

    return ENautilusSessionTreeResponse(
        session_id=session_id,
        nodes=nodes,
        edges=edges,
        root_ids=root_ids,
        decision_events=decision_events,
    )


def _match_chosen_point(
    chosen: dict[str, float] | None,
    options: list[dict[str, float]],
    tolerance: float = 1e-9,
) -> int | None:
    """Match a chosen point to one of the intermediate point options."""
    if chosen is None or not options:
        return None

    for idx, opt in enumerate(options):
        if set(chosen.keys()) == set(opt.keys()) and all(abs(chosen[k] - opt[k]) < tolerance for k in chosen):
            return idx

    return None
