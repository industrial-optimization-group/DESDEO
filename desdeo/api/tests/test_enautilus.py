"""Tests related to E-NAUTILUS models and routes."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from desdeo.api.models import EnautilusStepRequest, ProblemDB, RepresentativeNonDominatedSolutions, user

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

    request = EnautilusStepRequest(
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
        select(RepresentativeNonDominatedSolutions).where(ProblemDB.id == problem_db.id)
    ).first()

    current_iteration = 0
    total_iterations = 5
    selected_point = None  # nadir point
    reachable_point_indices = []  # empty for first iteration
    number_of_intermediate_points = 3

    request = EnautilusStepRequest(
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

    response = post_json(client, "/method/enautilus/step", request.model_dump(), access_token)
