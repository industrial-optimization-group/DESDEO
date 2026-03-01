"""Defines end-points to access functionalities related to the E-NAUTILUS method."""

from typing import Annotated

import numpy as np
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ENautilusRepresentativeSolutionsRequest,
    ENautilusRepresentativeSolutionsResponse,
    ENautilusState,
    ENautilusStateRequest,
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


@router.post("/get_state")
def get_state(
    request: ENautilusStateRequest,
    db_session: Annotated[Session, Depends(get_session)],
) -> ENautilusStateResponse:
    """Fetch a previous state of the the E-NAUTILUS method."""
    state_db: StateDB | None = db_session.exec(select(StateDB).where(StateDB.id == request.state_id)).first()

    if state_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find 'StateDB' with id={request.id}"
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


@router.post("/get_representative")
def get_representative(
    request: ENautilusRepresentativeSolutionsRequest, db_session: Annotated[Session, Depends(get_session)]
) -> ENautilusRepresentativeSolutionsResponse:
    """Computes the representative solutions that are closest to the intermediate solutions computed by E-NAUTILUS.

    This endpoint should be used to get the actual solution from the
    non-dominated representation used in the E-NAUTILUS method's last iteration
    (when number of iterations left is 0).

    Args:
        request (ENautilusRepresentativeSolutionsRequest): a request which
            contains the id of the `StateDB` with information on the intermediate
            points for which the representative solutions should be computed.
        db_session (Annotated[Session, Depends): the database session.

    Raises:
        HTTPException: 404 when a `StateDB`, `ProblemDB`, or
            `RepresentativeNonDominatedSolutions` instance cannot be found. 406 when
            the substate of the references `StateDB` is not an instance of
            `ENautilusState`.

    Returns:
        ENautilusRepresentativeSolutionsResponse: the information on the representative solutions.
    """
    state_db: StateDB | None = db_session.exec(select(StateDB).where(StateDB.id == request.state_id)).first()

    if state_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find 'StateDB' with id={request.id}"
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
