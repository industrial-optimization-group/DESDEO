"""Defines end-points to access functionalities related to the E-NAUTILUS method."""

from typing import Annotated

import numpy as np
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ENautilusFinalizeRequest,
    ENautilusFinalizeResponse,
    ENautilusFinalState,
    ENautilusRepresentativeSolutionsResponse,
    ENautilusState,
    ENautilusStateResponse,
    ENautilusStepRequest,
    ENautilusStepResponse,
    ProblemDB,
    RepresentativeNonDominatedSolutions,
    StateDB,
)
from desdeo.mcdm import ENautilusResult, enautilus_get_representative_solutions, enautilus_step
from desdeo.problem import Problem

from .utils import (
    SessionContext,
    get_session_context,
)

router = APIRouter(prefix="/method/enautilus")


@router.post("/step")
def step(
    request: ENautilusStepRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> ENautilusStepResponse:
    """Steps the E-NAUTILUS method."""
    # user = context.user  # not used here
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
    context: Annotated[SessionContext, Depends(get_session_context)],
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
