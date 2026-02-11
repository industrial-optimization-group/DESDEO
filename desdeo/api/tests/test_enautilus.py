"""Tests related to E-NAUTILUS models and routes."""

import json

import numpy as np
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from desdeo.api.models import (
    ENautilusFinalizeRequest,
    ENautilusFinalizeResponse,
    ENautilusFinalState,
    ENautilusRepresentativeSolutionsResponse,
    ENautilusStateResponse,
    ENautilusStepRequest,
    ENautilusStepResponse,
    ProblemDB,
    ProblemMetaDataDB,
    RepresentativeNonDominatedSolutions,
    StateDB,
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
    assert request.current_iteration == current_iteration
    assert request.iterations_left == iterations_left
    assert request.selected_point == selected_point
    assert request.reachable_point_indices == reachable_point_indices
    assert request.number_of_intermediate_points == number_of_intermediate_points


def test_enautilus_step_router(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test the E-NAUTILUS stepping endpoint."""
    session, _ = session_and_user["session"], session_and_user["user"]
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
    assert step_response.current_iteration == previous_step.current_iteration + 1  # advances by 1
    assert step_response.iterations_left == previous_step.iterations_left - 1  # decrement by 1
    assert len(step_response.intermediate_points) == new_number_of_intermediate_points
    assert len(step_response.reachable_best_bounds) == new_number_of_intermediate_points  # one for each point
    assert len(step_response.reachable_worst_bounds) == new_number_of_intermediate_points  # one for each point
    assert len(step_response.closeness_measures) == new_number_of_intermediate_points  # one for each point
    assert len(step_response.reachable_point_indices) == new_number_of_intermediate_points  # one set for each point


def test_enautilus_get_state(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test fetching a previous state for the the E-NAUTILUS method."""
    session, _ = session_and_user["session"], session_and_user["user"]
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

    session_id = None
    parent_state_id = None

    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=session_id,
        parent_state_id=parent_state_id,
        representative_solutions_id=representative_solutions.id,
        current_iteration=current_iteration,
        iterations_left=total_iterations,
        selected_point=selected_point,
        reachable_point_indices=reachable_point_indices,
        number_of_intermediate_points=number_of_intermediate_points,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)

    assert raw_response.status_code == 200  # OK

    step1_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    assert step1_response.state_id == 1  # there should be no prior StateDB in the test instance of the DB
    assert step1_response.current_iteration == current_iteration + 1  # advances by 1
    assert step1_response.iterations_left == total_iterations - 1  # decrement by 1
    assert len(step1_response.intermediate_points) == number_of_intermediate_points
    assert len(step1_response.reachable_best_bounds) == number_of_intermediate_points  # one for each point
    assert len(step1_response.reachable_worst_bounds) == number_of_intermediate_points  # one for each point
    assert len(step1_response.closeness_measures) == number_of_intermediate_points  # one for each point
    assert len(step1_response.reachable_point_indices) == number_of_intermediate_points  # one set for each point

    # second iteration
    previous_step = step1_response
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

    step2_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    assert step2_response.state_id == 2  # there should be one prior StateDB in the test instance of the DB
    assert step2_response.current_iteration == previous_step.current_iteration + 1  # advances by 1
    assert step2_response.iterations_left == previous_step.iterations_left - 1  # decrement by 1
    assert len(step2_response.intermediate_points) == new_number_of_intermediate_points
    assert len(step2_response.reachable_best_bounds) == new_number_of_intermediate_points  # one for each point
    assert len(step2_response.reachable_worst_bounds) == new_number_of_intermediate_points  # one for each point
    assert len(step2_response.closeness_measures) == new_number_of_intermediate_points  # one for each point
    assert len(step2_response.reachable_point_indices) == new_number_of_intermediate_points  # one set for each point

    raw_response = get_json(client, f"/method/enautilus/get_state/{step1_response.state_id}", access_token)

    assert raw_response.status_code == 200  # OK

    state_response = ENautilusStateResponse.model_validate(json.loads(raw_response.content))

    previous_request = state_response.request
    previous_response = state_response.response

    # response is the result of the state
    assert previous_response.state_id == step1_response.state_id
    assert previous_response.current_iteration == step1_response.current_iteration
    assert previous_response.iterations_left == step1_response.iterations_left
    assert previous_response.intermediate_points == step1_response.intermediate_points
    assert previous_response.reachable_best_bounds == step1_response.reachable_best_bounds
    assert previous_response.reachable_worst_bounds == step1_response.reachable_worst_bounds
    assert previous_response.closeness_measures == step1_response.closeness_measures
    assert previous_response.reachable_point_indices == step1_response.reachable_point_indices

    nadir_point = {
        f"{obj.symbol}": (-1 if obj.maximize else 1)
        * np.max(representative_solutions.solution_data[f"{obj.symbol}_min"])
        for obj in problem_db.objectives
    }

    reachable_point_indices_ = list(range(len(representative_solutions.solution_data[problem_db.objectives[0].symbol])))

    # request is the origin of the state
    assert previous_request.problem_id == problem_db.id
    assert previous_request.session_id == session_id
    assert previous_request.parent_state_id == parent_state_id
    assert previous_request.representative_solutions_id == representative_solutions.id
    assert previous_request.current_iteration == current_iteration
    assert previous_request.iterations_left == total_iterations
    assert previous_request.selected_point == nadir_point  # should be the nadir, because first iteration
    assert previous_request.reachable_point_indices == reachable_point_indices_  # all in the first iteration
    assert previous_request.number_of_intermediate_points == number_of_intermediate_points


def test_enautilus_get_representative(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test the E-NAUTILUS endpoint for getting representative solutions."""
    session, _ = session_and_user["session"], session_and_user["user"]
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

    # iterate until last
    while step_response.iterations_left > 0:
        previous_step = step_response

        request = ENautilusStepRequest(
            problem_id=problem_db.id,
            session_id=None,
            parent_state_id=previous_step.state_id,
            representative_solutions_id=representative_solutions.id,
            current_iteration=previous_step.current_iteration,
            iterations_left=previous_step.iterations_left,
            selected_point=previous_step.intermediate_points[0],
            reachable_point_indices=previous_step.reachable_point_indices[0],
            number_of_intermediate_points=number_of_intermediate_points,
        )

        raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)

        assert raw_response.status_code == 200  # OK

        step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    # no iterations left, last iteration
    raw_response = get_json(client, "/method/enautilus/get_representative/3", access_token)

    assert raw_response.status_code == 200

    int_response = ENautilusRepresentativeSolutionsResponse.model_validate(json.loads(raw_response.content))

    assert len(int_response.solutions) == number_of_intermediate_points

    # try also a previous iteration
    raw_response = get_json(client, "/method/enautilus/get_representative/2", access_token)

    assert raw_response.status_code == 200

    int_response = ENautilusRepresentativeSolutionsResponse.model_validate(json.loads(raw_response.content))

    assert len(int_response.solutions) == number_of_intermediate_points


def test_enautilus_finalize_request_model():
    """Test the ENautilusFinalizeRequest model."""
    request = ENautilusFinalizeRequest(
        problem_id=1,
        session_id=2,
        parent_state_id=10,
        selected_point_index=0,
    )

    assert request.problem_id == 1
    assert request.session_id == 2
    assert request.parent_state_id == 10
    assert request.selected_point_index == 0


def test_enautilus_final_state_persisted(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test that ENautilusFinalState is correctly persisted in the database."""
    session, _ = session_and_user["session"], session_and_user["user"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    representative_solutions = session.exec(
        select(RepresentativeNonDominatedSolutions)
        .join(RepresentativeNonDominatedSolutions.metadata_instance)
        .where(ProblemMetaDataDB.problem_id == problem_db.id)
    ).first()

    # Single iteration to reach iterations_left == 0
    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=None,
        representative_solutions_id=representative_solutions.id,
        current_iteration=0,
        iterations_left=1,
        selected_point=None,
        reachable_point_indices=[],
        number_of_intermediate_points=2,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)
    assert raw_response.status_code == 200
    step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    # Finalize
    finalize_request = ENautilusFinalizeRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=step_response.state_id,
        selected_point_index=0,
    )

    raw_response = post_json(client, "/method/enautilus/finalize", finalize_request.model_dump(), access_token)
    assert raw_response.status_code == 200
    finalize_response = ENautilusFinalizeResponse.model_validate(json.loads(raw_response.content))

    # Verify the ENautilusFinalState was persisted correctly
    state_db = session.exec(select(StateDB).where(StateDB.id == finalize_response.state_id)).first()
    assert state_db is not None

    # Get the concrete final state
    final_state: ENautilusFinalState = state_db.state
    assert final_state is not None
    assert isinstance(final_state, ENautilusFinalState)

    # Verify all fields were persisted
    assert final_state.origin_step_state_id == step_response.state_id
    assert final_state.selected_point_index == 0
    assert final_state.selected_intermediate_point == step_response.intermediate_points[0]
    assert final_state.solver_results is not None
    assert final_state.solver_results.optimal_objectives is not None
    assert final_state.solver_results.optimal_variables is not None

    # Verify the ResultInterface properties work
    assert final_state.num_solutions == 1
    assert len(final_state.result_objective_values) == 1
    assert len(final_state.result_variable_values) == 1


def test_enautilus_finalize_endpoint(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test the E-NAUTILUS finalize endpoint - happy path."""
    session, _ = session_and_user["session"], session_and_user["user"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    representative_solutions = session.exec(
        select(RepresentativeNonDominatedSolutions)
        .join(RepresentativeNonDominatedSolutions.metadata_instance)
        .where(ProblemMetaDataDB.problem_id == problem_db.id)
    ).first()

    # Run E-NAUTILUS until iterations_left == 0
    current_iteration = 0
    total_iterations = 3  # Use fewer iterations for faster test
    number_of_intermediate_points = 2

    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=None,
        representative_solutions_id=representative_solutions.id,
        current_iteration=current_iteration,
        iterations_left=total_iterations,
        selected_point=None,
        reachable_point_indices=[],
        number_of_intermediate_points=number_of_intermediate_points,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)
    assert raw_response.status_code == 200
    step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    # Iterate until last iteration (iterations_left == 0)
    while step_response.iterations_left > 0:
        previous_step = step_response

        request = ENautilusStepRequest(
            problem_id=problem_db.id,
            session_id=None,
            parent_state_id=previous_step.state_id,
            representative_solutions_id=representative_solutions.id,
            current_iteration=previous_step.current_iteration,
            iterations_left=previous_step.iterations_left,
            selected_point=previous_step.intermediate_points[0],
            reachable_point_indices=previous_step.reachable_point_indices[0],
            number_of_intermediate_points=number_of_intermediate_points,
        )

        raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)
        assert raw_response.status_code == 200
        step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    # Now iterations_left == 0, we can finalize
    assert step_response.iterations_left == 0
    last_state_id = step_response.state_id

    # Finalize by selecting the first intermediate point
    finalize_request = ENautilusFinalizeRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=last_state_id,
        selected_point_index=0,
    )

    raw_response = post_json(client, "/method/enautilus/finalize", finalize_request.model_dump(), access_token)

    assert raw_response.status_code == 200

    finalize_response = ENautilusFinalizeResponse.model_validate(json.loads(raw_response.content))

    assert finalize_response.response_type == "e-nautilus.finalize"
    assert finalize_response.state_id is not None
    assert finalize_response.state_id > last_state_id  # New state created
    assert finalize_response.selected_intermediate_point == step_response.intermediate_points[0]
    assert finalize_response.final_solution is not None
    assert finalize_response.final_solution.optimal_objectives is not None
    assert finalize_response.final_solution.optimal_variables is not None


def test_enautilus_finalize_invalid_iterations_left(
    client: TestClient, session_and_user: dict[str, Session | list[user]]
):
    """Test that finalize fails when iterations_left != 0."""
    session, _ = session_and_user["session"], session_and_user["user"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    representative_solutions = session.exec(
        select(RepresentativeNonDominatedSolutions)
        .join(RepresentativeNonDominatedSolutions.metadata_instance)
        .where(ProblemMetaDataDB.problem_id == problem_db.id)
    ).first()

    # Create a step state with iterations_left > 0
    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=None,
        representative_solutions_id=representative_solutions.id,
        current_iteration=0,
        iterations_left=5,  # More than 0
        selected_point=None,
        reachable_point_indices=[],
        number_of_intermediate_points=2,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)
    assert raw_response.status_code == 200
    step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    # Try to finalize when iterations_left != 0
    assert step_response.iterations_left > 0  # Confirm it's not 0

    finalize_request = ENautilusFinalizeRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=step_response.state_id,
        selected_point_index=0,
    )

    raw_response = post_json(client, "/method/enautilus/finalize", finalize_request.model_dump(), access_token)

    assert raw_response.status_code == 400  # Bad Request
    error_detail = json.loads(raw_response.content)["detail"]
    assert "iterations_left" in error_detail
    assert "must be 0" in error_detail


def test_enautilus_finalize_invalid_point_index(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test that finalize fails with an invalid selected_point_index."""
    session, _ = session_and_user["session"], session_and_user["user"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    representative_solutions = session.exec(
        select(RepresentativeNonDominatedSolutions)
        .join(RepresentativeNonDominatedSolutions.metadata_instance)
        .where(ProblemMetaDataDB.problem_id == problem_db.id)
    ).first()

    # Run E-NAUTILUS until iterations_left == 0
    number_of_intermediate_points = 2

    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=None,
        representative_solutions_id=representative_solutions.id,
        current_iteration=0,
        iterations_left=1,  # Single iteration to reach 0 quickly
        selected_point=None,
        reachable_point_indices=[],
        number_of_intermediate_points=number_of_intermediate_points,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)
    assert raw_response.status_code == 200
    step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    assert step_response.iterations_left == 0

    # Try to finalize with an invalid index (too high)
    finalize_request = ENautilusFinalizeRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=step_response.state_id,
        selected_point_index=999,  # Invalid - only 2 intermediate points
    )

    raw_response = post_json(client, "/method/enautilus/finalize", finalize_request.model_dump(), access_token)

    assert raw_response.status_code == 400  # Bad Request
    error_detail = json.loads(raw_response.content)["detail"]
    assert "Invalid selected_point_index" in error_detail


def test_enautilus_finalize_second_option(client: TestClient, session_and_user: dict[str, Session | list[user]]):
    """Test finalizing with a different selected_point_index."""
    session, _ = session_and_user["session"], session_and_user["user"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    representative_solutions = session.exec(
        select(RepresentativeNonDominatedSolutions)
        .join(RepresentativeNonDominatedSolutions.metadata_instance)
        .where(ProblemMetaDataDB.problem_id == problem_db.id)
    ).first()

    number_of_intermediate_points = 3

    # Single iteration to reach iterations_left == 0
    request = ENautilusStepRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=None,
        representative_solutions_id=representative_solutions.id,
        current_iteration=0,
        iterations_left=1,
        selected_point=None,
        reachable_point_indices=[],
        number_of_intermediate_points=number_of_intermediate_points,
    )

    raw_response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)
    assert raw_response.status_code == 200
    step_response = ENautilusStepResponse.model_validate(json.loads(raw_response.content))

    assert step_response.iterations_left == 0
    assert len(step_response.intermediate_points) == number_of_intermediate_points

    # Finalize by selecting the second intermediate point (index 1)
    finalize_request = ENautilusFinalizeRequest(
        problem_id=problem_db.id,
        session_id=None,
        parent_state_id=step_response.state_id,
        selected_point_index=1,  # Second option
    )

    raw_response = post_json(client, "/method/enautilus/finalize", finalize_request.model_dump(), access_token)

    assert raw_response.status_code == 200

    finalize_response = ENautilusFinalizeResponse.model_validate(json.loads(raw_response.content))

    assert finalize_response.selected_intermediate_point == step_response.intermediate_points[1]
    assert finalize_response.final_solution is not None
