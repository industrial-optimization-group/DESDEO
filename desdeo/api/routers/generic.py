"""Defines end-points to access generic functionalities."""

from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from desdeo.api.models import (
    IntermediateSolutionRequest,
    IntermediateSolutionState,
    ScoreBandsRequest,
    ScoreBandsResponse,
    SolutionReference,
    StateDB,
)
from desdeo.api.models.generic import GenericIntermediateSolutionResponse
from desdeo.mcdm.nimbus import solve_intermediate_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults
from desdeo.tools.score_bands import calculate_axes_positions, cluster, order_dimensions

from .utils import SessionContext, get_session_context

router = APIRouter(prefix="/method/generic")


@router.post("/intermediate")
def solve_intermediate(
    request: IntermediateSolutionRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> GenericIntermediateSolutionResponse:
    """Solve intermediate solutions between given two solutions.

    Args:
        request (IntermediateSolutionRequest): The request object containing parameters
            for fetching results.
        context (Annotated[SessionContext, Depends]): The session context.
    """
    db_session = context.db_session
    problem_db = context.problem_db
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    # --------------------------------------
    # Validate interactive session
    # --------------------------------------
    if interactive_session is None and request.session_id is not None:
        # session id was explicitly requested but not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find interactive session with id={request.session_id}.",
        )

    # --------------------------------------
    # query both reference solutions' variable values
    # --------------------------------------
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
                detail=(
                    f"The index {solution_info.solution_index} is out of bounds for results with len={len(_var_values)}"
                ),
            ) from exc

        try:
            _obj_values = solution_state.state.result_objective_values
            obj_values = _obj_values[solution_info.solution_index]
        except IndexError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"The index {solution_info.solution_index} is out of bounds for results with len={len(_obj_values)}"
                ),
            ) from exc

        var_and_obj_values_of_references.append((var_values, obj_values))

    # --------------------------------------
    # Problem is now already loaded via context
    # --------------------------------------
    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
        )

    problem = Problem.from_problemdb(problem_db)

    solver_results: list[SolverResults] = solve_intermediate_solutions(
        problem=problem,
        solution_1=var_and_obj_values_of_references[0][0],
        solution_2=var_and_obj_values_of_references[1][0],
        num_desired=request.num_desired,
        scalarization_options=request.scalarization_options,
        solver=request.solver,
        solver_options=request.solver_options,
    )

    # --------------------------------------
    # parent_state is already loaded in context
    # --------------------------------------
    intermediate_state = IntermediateSolutionState(
        scalarization_options=request.scalarization_options,
        context=request.context,
        solver=request.solver,
        solver_options=request.solver_options,
        solver_results=solver_results,
        num_desired=request.num_desired,
        reference_solution_1=var_and_obj_values_of_references[0][1],
        reference_solution_2=var_and_obj_values_of_references[1][1],
    )

    # create DB state and add it to the DB
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

    return GenericIntermediateSolutionResponse(
        state_id=state.id,
        reference_solution_1=SolutionReference(
            state=reference_states[0],
            solution_index=request.reference_solution_1.solution_index,
            name=request.reference_solution_1.name,
        ),
        reference_solution_2=SolutionReference(
            state=reference_states[1],
            solution_index=request.reference_solution_2.solution_index,
            name=request.reference_solution_2.name,
        ),
        intermediate_solutions=[
            SolutionReference(state=state, solution_index=i) for i in range(state.state.num_solutions)
        ],
    )


@router.post("/score-bands-obj-data")
def calculate_score_bands_from_objective_data(
    request: ScoreBandsRequest,
) -> ScoreBandsResponse:
    """Calculate SCORE bands parameters from objective data."""
    try:
        # Convert input data to pandas DataFrame
        data = pd.DataFrame(request.data, columns=request.objs)

        # Calculate correlation matrix and objective order
        corr, obj_order = order_dimensions(data, use_absolute_corr=request.use_absolute_corr)

        # Calculate axis positions and signs
        ordered_data, axis_dist, axis_signs = calculate_axes_positions(
            data,
            obj_order,
            corr,
            dist_parameter=request.dist_parameter,
            distance_formula=request.distance_formula,
        )

        # Handle flip_axes parameter - if flip_axes is False, don't use axis signs
        if not request.flip_axes:
            axis_signs = None

        # Perform clustering
        groups = cluster(
            ordered_data,
            algorithm=request.clustering_algorithm,
            score=request.clustering_score,
        )

        # Translate minimum group to 1 (as done in the notebook)
        groups = groups - np.min(groups) + 1

        # Convert numpy arrays to lists for JSON serialization
        # Handle potential None values and ensure proper type conversion
        return ScoreBandsResponse(
            groups=groups.tolist() if hasattr(groups, "tolist") else list(groups),
            axis_dist=(axis_dist.tolist() if hasattr(axis_dist, "tolist") else list(axis_dist)),
            axis_signs=(
                axis_signs.tolist()
                if axis_signs is not None and hasattr(axis_signs, "tolist")
                else (list(axis_signs) if axis_signs is not None else None)
            ),
            obj_order=(obj_order.tolist() if hasattr(obj_order, "tolist") else list(obj_order)),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error calculating SCORE bands parameters: {e!r}",
        ) from e
