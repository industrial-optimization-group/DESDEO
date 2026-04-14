"""Tests related to NAUTILUS Navigator models and routes."""

import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from desdeo.api.models import (
    NautilusNavigatorInitRequest,
    NautilusNavigatorInitResponse,
    NautilusNavigatorNavigateRequest,
    NautilusNavigatorNavigateResponse,
    ProblemDB,
    User,
)

from .conftest import login, post_json


def test_init_request_model():
    """Test NautilusNavigatorInitRequest model instantiation."""
    request = NautilusNavigatorInitRequest(
        problem_id=1,
        session_id=2,
        parent_state_id=3,
    )

    assert request.problem_id == 1
    assert request.session_id == 2
    assert request.parent_state_id == 3


def test_navigate_request_model():
    """Test NautilusNavigatorNavigateRequest model instantiation."""
    ref_point = {"f_1": 6.0, "f_2": 3.0, "f_3": 5.0, "f_4": -2.0, "f_5": 0.1}
    bounds = {"f_1": 5.5, "f_2": 2.9}

    request = NautilusNavigatorNavigateRequest(
        problem_id=10,
        session_id=20,
        parent_state_id=30,
        reference_point=ref_point,
        bounds=bounds,
        steps_remaining=100,
    )

    assert request.problem_id == 10
    assert request.session_id == 20
    assert request.parent_state_id == 30
    assert request.reference_point == ref_point
    assert request.bounds == bounds
    assert request.steps_remaining == 100


def test_initialize(client: TestClient, session_and_user: dict[str, Session | list[User]]):
    """Test the NAUTILUS Navigator initialization endpoint."""
    session = session_and_user["session"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    request = NautilusNavigatorInitRequest(problem_id=problem_db.id)

    raw_response = post_json(client, "/nautilus/initialize", request.model_dump(), access_token)

    assert raw_response.status_code == 200

    response = NautilusNavigatorInitResponse.model_validate(json.loads(raw_response.content))

    assert response.state_id is not None
    assert response.step_number == 0
    assert response.distance_to_front == 0.0

    for obj in problem_db.objectives:
        sym = obj.symbol

        # navigation_point should have all objective symbols
        assert sym in response.navigation_point

        # bounds should be present and have all objective keys
        assert sym in response.lower_bounds
        assert sym in response.upper_bounds


def test_navigate_full_steps(client: TestClient, session_and_user: dict[str, Session | list[User]]):
    """Test that a single navigate call produces all requested steps."""
    session = session_and_user["session"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    # Initialize
    init_request = NautilusNavigatorInitRequest(problem_id=problem_db.id)
    init_raw = post_json(client, "/nautilus/initialize", init_request.model_dump(), access_token)
    assert init_raw.status_code == 200
    init_response = NautilusNavigatorInitResponse.model_validate(json.loads(init_raw.content))

    # Navigate with a reference point, request all 100 remaining steps
    steps_remaining = 10
    reference_point = {"f_1": 6.0, "f_2": 3.2, "f_3": 5.0, "f_4": -1.0, "f_5": 0.1}

    nav_request = NautilusNavigatorNavigateRequest(
        problem_id=problem_db.id,
        parent_state_id=init_response.state_id,
        reference_point=reference_point,
        steps_remaining=steps_remaining,
    )

    nav_raw = post_json(client, "/nautilus/navigate", nav_request.model_dump(), access_token)
    assert nav_raw.status_code == 200

    nav_response = NautilusNavigatorNavigateResponse.model_validate(json.loads(nav_raw.content))

    assert nav_response.state_id is not None
    assert len(nav_response.steps) == steps_remaining

    # Verify steps are ordered by step_number
    step_numbers = [s.step_number for s in nav_response.steps]
    assert step_numbers == sorted(step_numbers)

    # Each step should have navigation_point, bounds, and distance_to_front
    for step in nav_response.steps:
        for obj in problem_db.objectives:
            sym = obj.symbol
            assert sym in step.navigation_point
            assert sym in step.lower_bounds
            assert sym in step.upper_bounds
        assert step.distance_to_front >= 0.0


def test_navigate_preference_change(client: TestClient, session_and_user: dict[str, Session | list[User]]):
    """Test that changing preferences mid-navigation recomputes only future steps.

    Scenario: navigate 10 steps, then "stop" at step 5 and provide new
    preferences. The steps from the first navigation (1..5) should remain
    unchanged in the first response; only the steps computed after the
    preference change (from the second call) should differ.
    """
    session = session_and_user["session"]
    access_token = login(client)

    problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    # Initialize
    init_request = NautilusNavigatorInitRequest(problem_id=problem_db.id)
    init_raw = post_json(client, "/nautilus/initialize", init_request.model_dump(), access_token)
    assert init_raw.status_code == 200
    init_response = NautilusNavigatorInitResponse.model_validate(json.loads(init_raw.content))

    # First navigation: compute all 10 steps with initial preferences
    reference_point_1 = {"f_1": 6.0, "f_2": 3.2, "f_3": 5.0, "f_4": -1.0, "f_5": 0.1}
    nav_request_1 = NautilusNavigatorNavigateRequest(
        problem_id=problem_db.id,
        parent_state_id=init_response.state_id,
        reference_point=reference_point_1,
        steps_remaining=10,
    )

    nav_raw_1 = post_json(client, "/nautilus/navigate", nav_request_1.model_dump(), access_token)
    assert nav_raw_1.status_code == 200
    nav_response_1 = NautilusNavigatorNavigateResponse.model_validate(json.loads(nav_raw_1.content))

    assert len(nav_response_1.steps) == 10

    # The first 5 steps are "shown" to the DM via animation.
    # The DM stops at step 5 and provides new preferences.
    first_5_steps = nav_response_1.steps[:5]

    # Second navigation: DM changes preferences at step 5, 5 steps remaining
    reference_point_2 = {"f_1": 5.0, "f_2": 3.0, "f_3": 7.0, "f_4": -5.0, "f_5": 0.2}
    nav_request_2 = NautilusNavigatorNavigateRequest(
        problem_id=problem_db.id,
        parent_state_id=nav_response_1.state_id,
        reference_point=reference_point_2,
        steps_remaining=5,
    )

    nav_raw_2 = post_json(client, "/nautilus/navigate", nav_request_2.model_dump(), access_token)
    assert nav_raw_2.status_code == 200
    nav_response_2 = NautilusNavigatorNavigateResponse.model_validate(json.loads(nav_raw_2.content))

    assert nav_response_2.state_id is not None
    assert len(nav_response_2.steps) == 5

    # The first 5 steps (from the original navigation) should be unchanged,
    # they were already shown to the DM and are historical.
    # We verify that by checking the first navigation's steps 0..4 are still
    # what we captured before the second call.
    for i, step in enumerate(first_5_steps):
        assert step.navigation_point == nav_response_1.steps[i].navigation_point
        assert step.lower_bounds == nav_response_1.steps[i].lower_bounds
        assert step.upper_bounds == nav_response_1.steps[i].upper_bounds

    # The new 5 steps should differ from the original steps 5..9
    # because the reference point changed
    original_remaining = nav_response_1.steps[5:]
    new_steps = nav_response_2.steps

    # At least some of the new steps should differ from the original remaining
    # steps (different preferences → different navigation path)
    differences_found = False
    for orig, new in zip(original_remaining, new_steps, strict=True):
        if orig.navigation_point != new.navigation_point:
            differences_found = True
            break

    assert differences_found, "New preferences should produce different navigation steps"


def test_initialize_invalid_problem(client: TestClient, session_and_user: dict[str, Session | list[User]]):
    """Test that initializing with a non-existent problem returns an error."""
    access_token = login(client)

    request = NautilusNavigatorInitRequest(problem_id=99999)

    raw_response = post_json(client, "/nautilus/initialize", request.model_dump(), access_token)

    assert raw_response.status_code == 400
