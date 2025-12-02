"""Tests related to E-NAUTILUS models and routes."""

import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from desdeo.api.models import (
    ENautilusStepRequest,
    ENautilusStepResponse,
    ProblemDB,
    ProblemMetaDataDB,
    RepresentativeNonDominatedSolutions,
    user,
)

from .conftest import get_json, login, post_json


def test_enautilus_step_request(session_and_user: dict[str, Session | list[user]]):
    """Tests the E-NAUTILUS step request model."""
    problem_id = 42
    session_id = 69
    parent_state_id = 20
    representative_solutions_id = 10

    current_iteration = 3
    iterations_left = 4
    selected_point = {"f_1": 2.3, "f_2": 4.3, "f_3": -22222.3}
    reachable_point_indices = [1, 2, 3, 46, 9]
    number_of_intermediate_points = 9001

    request = ENautilusStepRequest(
        problem_id=problem_id,
        session_id=session_id,
        parent_state_id=parent_state_id,
        representative_solutions_id=representative_solutions_id,
        current_iteration=current_iteration,
        iterations_left=iterations_left,
        selected_point=selected_point,
        reachable_point_indices=reachable_point_indices,
        number_of_intermediate_points=number_of_intermediate_points,
    )

    assert request.problem_id == problem_id
    assert request.session_id == session_id
    assert request.parent_state_id == parent_state_id
    assert request.representative_solutions_id == representative_solutions_id
    assert request.current_iteration == current_iteration
    assert request.iterations_left == iterations_left
    assert request.selected_point == selected_point
    assert request.reachable_point_indices == reachable_point_indices
    assert request.number_of_intermediate_points == number_of_intermediate_points


def test_enautilus_step_router(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test the E-NAUTILUS stepping endpoint."""
    session, user = session_and_user["session"], session_and_user["user"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    representative_solutions = session.exec(
        select(RepresentativeNonDominatedSolutions)
        .join(RepresentativeNonDominatedSolutions.metadata_instance)
        .where(ProblemMetaDataDB.problem_id == problem_db.id)
    ).first()

    current_iteration = 0
    total_iterations = 5
    selected_point = None  # nadir point
    reachable_point_indices = []  # empty for first iteration
    number_of_intermediate_points = 3

    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=None,
        representative_solutions_id=representative_solutions.id,
        current_iteration=current_iteration,
        iterations_left=total_iterations,
        selected_point=selected_point,
        reachable_point_indices=reachable_point_indices,
        number_of_intermediate_points=number_of_intermediate_points,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)

    assert raw_response.status_code == 200  # OK

    step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    assert step_response.state_id == 1  # there should be no prior StateDB in the test instance of the DB
    assert step_response.representative_solutions_id == representative_solutions.id
    assert step_response.current_iteration == current_iteration + 1  # advances by 1
    assert step_response.iterations_left == total_iterations - 1  # decrement by 1
    assert len(step_response.intermediate_points) == number_of_intermediate_points
    assert len(step_response.reachable_best_bounds) == number_of_intermediate_points  # one for each point
    assert len(step_response.reachable_worst_bounds) == number_of_intermediate_points  # one for each point
    assert len(step_response.closeness_measures) == number_of_intermediate_points  # one for each point
    assert len(step_response.reachable_point_indices) == number_of_intermediate_points  # one set for each point

    # second iteration
    previous_step = step_response
    new_number_of_intermediate_points = 2

    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=previous_step.state_id,
        representative_solutions_id=representative_solutions.id,
        current_iteration=previous_step.current_iteration,
        iterations_left=previous_step.iterations_left,
        selected_point=previous_step.intermediate_points[0],
        reachable_point_indices=previous_step.reachable_point_indices[0],
        number_of_intermediate_points=new_number_of_intermediate_points,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)

    assert raw_response.status_code == 200  # OK

    step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    assert step_response.state_id == 2  # there should be one prior StateDB in the test instance of the DB
    assert step_response.representative_solutions_id == representative_solutions.id
    assert step_response.current_iteration == previous_step.current_iteration + 1  # advances by 1
    assert step_response.iterations_left == previous_step.iterations_left - 1  # decrement by 1
    assert len(step_response.intermediate_points) == new_number_of_intermediate_points
    assert len(step_response.reachable_best_bounds) == new_number_of_intermediate_points  # one for each point
    assert len(step_response.reachable_worst_bounds) == new_number_of_intermediate_points  # one for each point
    assert len(step_response.closeness_measures) == new_number_of_intermediate_points  # one for each point
    assert len(step_response.reachable_point_indices) == new_number_of_intermediate_points  # one set for each point
