"""Tests for analyst adding problems on behalf of decision makers."""

from fastapi import status
from fastapi.testclient import TestClient

from desdeo.api.models import ProblemInfo, UserPublic, UserRole
from desdeo.problem.testproblems import simple_knapsack_vectors

from .conftest import get_json, login, post_file_multipart, post_json


def _add_dm(client: TestClient, analyst_token: str, username: str, password: str) -> None:
    """Helper: create a DM user via the API."""
    response = client.post(
        "/add_new_dm",
        data={"username": username, "password": password, "grant_type": "password"},
        headers={"Authorization": f"Bearer {analyst_token}", "content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_list_dms_as_analyst(client: TestClient):
    """Analyst can retrieve the list of DM users."""
    analyst_token = login(client)

    # No DMs yet — list should be empty
    response = get_json(client, "/users/dms", analyst_token)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # Create two DM users
    _add_dm(client, analyst_token, "dm_one", "dm_one")
    _add_dm(client, analyst_token, "dm_two", "dm_two")

    response = get_json(client, "/users/dms", analyst_token)
    assert response.status_code == status.HTTP_200_OK

    dms = [UserPublic.model_validate(u) for u in response.json()]
    usernames = {dm.username for dm in dms}
    assert usernames == {"dm_one", "dm_two"}
    assert all(dm.role == UserRole.dm for dm in dms)


def test_list_dms_as_dm_forbidden(client: TestClient):
    """DM users cannot list other DM users."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_user", "dm_user")

    dm_token = login(client, username="dm_user", password="dm_user")  # noqa: S106
    response = get_json(client, "/users/dms", dm_token)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_dms_unauthenticated(client: TestClient):
    """Unauthenticated requests to /users/dms are rejected."""
    response = client.get("/users/dms")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_add_problem_for_dm_as_analyst(client: TestClient, session_and_user: dict):
    """Analyst can add a problem that is owned by a DM."""
    analyst_token = login(client)

    # Create a DM
    _add_dm(client, analyst_token, "target_dm", "target_dm")
    dm_token = login(client, username="target_dm", password="target_dm")  # noqa: S106

    # Fetch DM id from /users/dms
    dms = get_json(client, "/users/dms", analyst_token).json()
    dm_id = next(u["id"] for u in dms if u["username"] == "target_dm")

    # Analyst submits a problem on behalf of the DM
    problem = simple_knapsack_vectors()
    response = post_json(client, f"/problem/add?target_user_id={dm_id}", problem.model_dump(), analyst_token)
    assert response.status_code == status.HTTP_200_OK

    info = ProblemInfo.model_validate(response.json())
    assert info.name == "Simple two-objective Knapsack problem"

    # DM should now own the problem
    dm_problems = get_json(client, "/problem/all", dm_token).json()
    assert any(p["name"] == "Simple two-objective Knapsack problem" for p in dm_problems)

    # Analyst should NOT own the problem
    analyst_problems = get_json(client, "/problem/all", analyst_token).json()
    assert not any(p["name"] == "Simple two-objective Knapsack problem" for p in analyst_problems)


def test_add_problem_for_dm_as_dm_forbidden(client: TestClient):
    """A DM cannot add a problem on behalf of another user."""
    analyst_token = login(client)

    # Create two DMs
    _add_dm(client, analyst_token, "dm_a", "dm_a")
    _add_dm(client, analyst_token, "dm_b", "dm_b")

    # Fetch dm_b's id
    dms = get_json(client, "/users/dms", analyst_token).json()
    dm_b_id = next(u["id"] for u in dms if u["username"] == "dm_b")

    # dm_a tries to add a problem for dm_b — should be forbidden
    dm_a_token = login(client, username="dm_a", password="dm_a")  # noqa: S106
    problem = simple_knapsack_vectors()
    response = post_json(client, f"/problem/add?target_user_id={dm_b_id}", problem.model_dump(), dm_a_token)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_add_problem_for_nonexistent_user(client: TestClient):
    """Adding a problem for a non-existent target_user_id returns 404."""
    analyst_token = login(client)
    problem = simple_knapsack_vectors()
    response = post_json(client, "/problem/add?target_user_id=99999", problem.model_dump(), analyst_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_problem_json_for_dm_as_analyst(client: TestClient):
    """Analyst can upload a JSON problem file on behalf of a DM."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "json_dm", "json_dm")
    dm_token = login(client, username="json_dm", password="json_dm")  # noqa: S106

    dms = get_json(client, "/users/dms", analyst_token).json()
    dm_id = next(u["id"] for u in dms if u["username"] == "json_dm")

    # Serialize a problem to JSON bytes
    problem = simple_knapsack_vectors()
    problem_bytes = problem.model_dump_json(by_alias=True).encode()

    response = post_file_multipart(
        client,
        f"/problem/add_json?target_user_id={dm_id}",
        problem_bytes,
        analyst_token,
    )
    assert response.status_code == status.HTTP_200_OK

    info = ProblemInfo.model_validate(response.json())
    assert info.name == "Simple two-objective Knapsack problem"

    # DM should own the problem
    dm_problems = get_json(client, "/problem/all", dm_token).json()
    assert any(p["name"] == "Simple two-objective Knapsack problem" for p in dm_problems)


def test_add_problem_json_for_dm_as_dm_forbidden(client: TestClient):
    """A DM cannot upload a JSON problem on behalf of another user."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "jdm_a", "jdm_a")
    _add_dm(client, analyst_token, "jdm_b", "jdm_b")

    dms = get_json(client, "/users/dms", analyst_token).json()
    jdm_b_id = next(u["id"] for u in dms if u["username"] == "jdm_b")

    jdm_a_token = login(client, username="jdm_a", password="jdm_a")  # noqa: S106
    problem = simple_knapsack_vectors()
    problem_bytes = problem.model_dump_json(by_alias=True).encode()

    response = post_file_multipart(
        client,
        f"/problem/add_json?target_user_id={jdm_b_id}",
        problem_bytes,
        jdm_a_token,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
