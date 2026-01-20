"""Defines end-points to access generic functionalities."""

from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    InteractiveSessionDB,
    IntermediateSolutionRequest,
    IntermediateSolutionState,
    ProblemDB,
    ScoreBandsRequest,
    ScoreBandsResponse,
    SolutionReference,
    StateDB,
    User,
)
from desdeo.api.models.generic import GenericIntermediateSolutionResponse
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.mcdm.nimbus import solve_intermediate_solutions
from desdeo.problem import Problem
from desdeo.tools import SolverResults
from desdeo.tools.score_bands import calculate_axes_positions, cluster, order_dimensions

router = APIRouter(prefix="/method/generic")


@router.post("/intermediate")
def solve_intermediate(
    request: IntermediateSolutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GenericIntermediateSolutionResponse:
    """Solve intermediate solutions between given two solutions."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == request.session_id)
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == user.active_session_id)

        interactive_session = session.exec(statement).first()

    # query both reference solutions' variable values
    # stored as lit of tuples, first element of each tuple are variables values, second are objective function values
    var_and_obj_values_of_references: list[tuple[dict, dict]] = []
    reference_states = []
    for solution_info in [request.reference_solution_1, request.reference_solution_2]:
        solution_state = session.exec(select(StateDB).where(StateDB.id == solution_info.state_id)).first()

        if solution_state is None:
            # no StateDB found with the given id
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find a state with the given id{solution_state.state_id}.",
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

    # fetch the problem from the DB
    statement = select(ProblemDB).where(ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id)
    problem_db = session.exec(statement).first()

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

    # fetch parent state
    if request.parent_state_id is None:
        # parent state is assumed to be the last state added to the session.
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )

    else:
        # request.parent_state_id is not None
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

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
        database_session=session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=intermediate_state,
    )

    session.add(state)
    session.commit()
    session.refresh(state)

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
