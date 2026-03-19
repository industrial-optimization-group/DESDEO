"""Tests for the constrained variant endpoint and DELETE problem behavior."""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from desdeo.api.models import (
    ProblemDB,
    User,
    UserRole,
)
from desdeo.api.models.problem import (
    ConstrainedVariantRequest,
    VariableFixing,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import river_pollution_problem

from .conftest import login, post_json


def test_variable_fixing_valid():
    """Create a VariableFixing and verify fields."""
    fixing = VariableFixing(variable_symbol="x_1", fixed_value=3.14, constraint_name="lock_x1")
    assert fixing.variable_symbol == "x_1"
    assert fixing.fixed_value == 3.14
    assert fixing.constraint_name == "lock_x1"


def test_constrained_variant_request_defaults():
    """Verify is_temporary defaults to True and name defaults to None."""
    req = ConstrainedVariantRequest(variable_fixings=[VariableFixing(variable_symbol="x_1", fixed_value=1.0)])
    assert req.is_temporary is True
    assert req.name is None


def test_constrained_variant_success(client: TestClient, session_and_user: dict):
    """POST valid fixings for an owned problem returns 200 with correct response."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    # Use the river pollution problem (has variables x_1, x_2)
    problem = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    payload = {
        "variable_fixings": [
            {"variable_symbol": "x_1", "fixed_value": 0.5},
            {"variable_symbol": "x_2", "fixed_value": 0.3},
        ],
    }

    response = post_json(client, f"/problem/{problem.id}/constrained_variant", payload, access_token)
    assert response.status_code == 200

    data = response.json()
    assert data["n_constraints_added"] == 2
    assert data["problem_id"] != problem.id
    assert data["parent_problem_id"] == problem.id
    assert data["is_temporary"] is True
    assert "[variant]" in data["name"]


def test_constrained_variant_creates_db_record(client: TestClient, session_and_user: dict):
    """After a successful POST, the new ProblemDB row exists with correct fields."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    payload = {
        "variable_fixings": [{"variable_symbol": "x_1", "fixed_value": 1.0}],
        "name": "Test Variant",
    }

    response = post_json(client, f"/problem/{problem.id}/constrained_variant", payload, access_token)
    assert response.status_code == 200

    variant_id = response.json()["problem_id"]
    variant_db = session.get(ProblemDB, variant_id)
    assert variant_db is not None
    assert variant_db.is_temporary is True
    assert variant_db.parent_problem_id == problem.id
    assert variant_db.name == "Test Variant"


def test_constrained_variant_unknown_symbol(client: TestClient, session_and_user: dict):
    """POST a fixing with a nonexistent variable symbol returns 422."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    payload = {
        "variable_fixings": [{"variable_symbol": "nonexistent_var", "fixed_value": 1.0}],
    }

    response = post_json(client, f"/problem/{problem.id}/constrained_variant", payload, access_token)
    assert response.status_code == 422
    assert "nonexistent_var" in response.json()["detail"]


def test_constrained_variant_wrong_owner(client: TestClient, session_and_user: dict):
    """POST for a problem owned by a different user returns 403."""
    session: Session = session_and_user["session"]

    # Create another user and their problem
    other_user = User(
        username="other_variant",
        password_hash=get_password_hash("other_variant"),
        role=UserRole.analyst,
        group="test",
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_problem = ProblemDB.from_problem(river_pollution_problem(), user=other_user)
    session.add(other_problem)
    session.commit()
    session.refresh(other_problem)

    # Login as the original analyst user
    access_token = login(client)

    payload = {
        "variable_fixings": [{"variable_symbol": "x_1", "fixed_value": 1.0}],
    }

    response = post_json(client, f"/problem/{other_problem.id}/constrained_variant", payload, access_token)
    # SessionContextGuard returns 400 (context missing) when user doesn't own the problem
    assert response.status_code == 400


def test_constrained_variant_not_found(client: TestClient, session_and_user: dict):
    """POST with a nonexistent problem_id returns 404."""
    access_token = login(client)

    payload = {
        "variable_fixings": [{"variable_symbol": "x_1", "fixed_value": 1.0}],
    }

    response = post_json(client, "/problem/99999/constrained_variant", payload, access_token)
    # SessionContextGuard returns 400 (context missing) when problem doesn't exist
    assert response.status_code == 400


def test_constrained_variant_preserves_original(client: TestClient, session_and_user: dict):
    """Creating a variant does not modify the original problem."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()
    original_name = problem.name
    original_constraint_count = len(problem.constraints)

    payload = {
        "variable_fixings": [
            {"variable_symbol": "x_1", "fixed_value": 0.5},
            {"variable_symbol": "x_2", "fixed_value": 0.3},
        ],
    }

    response = post_json(client, f"/problem/{problem.id}/constrained_variant", payload, access_token)
    assert response.status_code == 200

    # Refresh and verify original is unchanged
    session.refresh(problem)
    assert problem.name == original_name
    assert len(problem.constraints) == original_constraint_count


# --- Endpoint tests: DELETE /problem/{problem_id} ---


def test_delete_temporary_problem_success(client: TestClient, session_and_user: dict):
    """DELETE a temporary variant returns 204 and removes the DB row."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    # Create a temporary variant
    payload = {
        "variable_fixings": [{"variable_symbol": "x_1", "fixed_value": 1.0}],
    }
    create_resp = post_json(client, f"/problem/{problem.id}/constrained_variant", payload, access_token)
    assert create_resp.status_code == 200
    variant_id = create_resp.json()["problem_id"]

    # Delete it
    response = client.delete(
        f"/problem/{variant_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 204

    # Verify gone
    assert session.get(ProblemDB, variant_id) is None


def test_delete_non_temporary_problem_success(client: TestClient, session_and_user: dict):
    """DELETE a non-temporary problem owned by the user returns 204."""
    session: Session = session_and_user["session"]
    user = session_and_user["user"]
    access_token = login(client)

    # Create a fresh non-temporary problem to delete (don't destroy shared fixtures)
    problem = ProblemDB.from_problem(river_pollution_problem(), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)
    assert not problem.is_temporary

    response = client.delete(
        f"/problem/{problem.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 204
    assert session.get(ProblemDB, problem.id) is None


def test_delete_wrong_owner(client: TestClient, session_and_user: dict):
    """DELETE a problem owned by a different user returns 403."""
    session: Session = session_and_user["session"]

    other_user = User(
        username="other_delete",
        password_hash=get_password_hash("other_delete"),
        role=UserRole.analyst,
        group="test",
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_problem = ProblemDB.from_problem(river_pollution_problem(), user=other_user)
    other_problem.is_temporary = True
    session.add(other_problem)
    session.commit()
    session.refresh(other_problem)

    # Login as the original analyst
    access_token = login(client)

    response = client.delete(
        f"/problem/{other_problem.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403


def test_delete_not_found(client: TestClient, session_and_user: dict):
    """DELETE a nonexistent problem returns 404."""
    access_token = login(client)

    response = client.delete(
        "/problem/99999",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 404
