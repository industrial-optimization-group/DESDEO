"""Defines end-points to access functionalities related to the E-NAUTILUS method."""

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from desdeo.api.models import (
    ENautilusState,
    ENautilusStepRequest,
    ENautilusStepResponse,
    RepresentativeNonDominatedSolutions,
    StateDB,
)
from desdeo.mcdm import ENautilusResult, enautilus_step
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
        representative_solutions_id=representative_solutions.id,
        current_iteration=results.current_iteration,
        iterations_left=results.iterations_left,
        intermediate_points=results.intermediate_points,
        reachable_best_bounds=results.reachable_best_bounds,
        reachable_worst_bounds=results.reachable_worst_bounds,
        closeness_measures=results.closeness_measures,
        reachable_point_indices=results.reachable_point_indices,
    )
