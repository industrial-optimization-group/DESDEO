"""Tests for analyst/admin management of other users' interactive sessions."""

from fastapi import status
from fastapi.testclient import TestClient

from .conftest import get_json, login, post_json


def _add_dm(client: TestClient, analyst_token: str, username: str, password: str) -> None:
    """Helper: create a DM user via the API."""
    response = client.post(
        "/add_new_dm",
        data={"username": username, "password": password, "grant_type": "password"},
        headers={"Authorization": f"Bearer {analyst_token}", "content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_201_CREATED


def _create_session(client: TestClient, token: str, info: str | None = None) -> int:
    """Helper: create a session and return its id."""
    response = post_json(client, "/session/new", {"info": info}, token)
    assert response.status_code == status.HTTP_200_OK
    return response.json()["id"]


def test_analyst_sees_all_sessions(client: TestClient):
    """Analyst's GET /session/get_all includes sessions from DM users."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_list", "dm_list")
    dm_token = login(client, username="dm_list", password="dm_list")  # noqa: S106

    dm_session_id = _create_session(client, dm_token, "DM's session")

    response = get_json(client, "/session/get_all", analyst_token)
    assert response.status_code == status.HTTP_200_OK
    ids = [s["id"] for s in response.json()]
    assert dm_session_id in ids


def test_dm_sees_only_own_sessions(client: TestClient):
    """DM cannot see another DM's sessions in GET /session/get_all."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_x", "dm_x")
    _add_dm(client, analyst_token, "dm_y", "dm_y")

    dm_x_token = login(client, username="dm_x", password="dm_x")  # noqa: S106
    dm_y_token = login(client, username="dm_y", password="dm_y")  # noqa: S106

    dm_x_session_id = _create_session(client, dm_x_token)

    response = get_json(client, "/session/get_all", dm_y_token)
    assert response.status_code == status.HTTP_200_OK
    ids = [s["id"] for s in response.json()]
    assert dm_x_session_id not in ids


def test_empty_session_list_returns_ok(client: TestClient):
    """GET /session/get_all returns 200 + empty list when user has no sessions."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_empty", "dm_empty")
    dm_token = login(client, username="dm_empty", password="dm_empty")  # noqa: S106

    response = get_json(client, "/session/get_all", dm_token)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_analyst_creates_session_for_dm(client: TestClient):
    """Analyst can create a session owned by a DM via ?target_user_id=."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_target", "dm_target")
    dm_token = login(client, username="dm_target", password="dm_target")  # noqa: S106

    dms = get_json(client, "/users/dms", analyst_token).json()
    dm_id = next(u["id"] for u in dms if u["username"] == "dm_target")

    response = post_json(
        client,
        f"/session/new?target_user_id={dm_id}",
        {"info": "created by analyst"},
        analyst_token,
    )
    assert response.status_code == status.HTTP_200_OK
    session_data = response.json()
    assert session_data["user_id"] == dm_id

    # DM should see it in their own listing
    dm_sessions = get_json(client, "/session/get_all", dm_token).json()
    assert any(s["id"] == session_data["id"] for s in dm_sessions)


def test_dm_cannot_create_for_other_dm(client: TestClient):
    """DM cannot create a session for another user via ?target_user_id=."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_a", "dm_a")
    _add_dm(client, analyst_token, "dm_b", "dm_b")

    dms = get_json(client, "/users/dms", analyst_token).json()
    dm_b_id = next(u["id"] for u in dms if u["username"] == "dm_b")

    dm_a_token = login(client, username="dm_a", password="dm_a")  # noqa: S106
    response = post_json(
        client,
        f"/session/new?target_user_id={dm_b_id}",
        {"info": "should fail"},
        dm_a_token,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_session_for_nonexistent_user(client: TestClient):
    """Creating a session with a nonexistent target_user_id returns 404."""
    analyst_token = login(client)
    response = post_json(client, "/session/new?target_user_id=99999", {"info": None}, analyst_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_analyst_can_get_dm_session_by_id(client: TestClient):
    """Analyst can GET a DM's session by its ID."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_get", "dm_get")
    dm_token = login(client, username="dm_get", password="dm_get")  # noqa: S106

    dm_session_id = _create_session(client, dm_token)

    response = get_json(client, f"/session/get/{dm_session_id}", analyst_token)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == dm_session_id


def test_dm_cannot_get_other_dm_session_by_id(client: TestClient):
    """DM cannot GET another DM's session by ID."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_owner", "dm_owner")
    _add_dm(client, analyst_token, "dm_thief", "dm_thief")

    owner_token = login(client, username="dm_owner", password="dm_owner")  # noqa: S106
    thief_token = login(client, username="dm_thief", password="dm_thief")  # noqa: S106

    owner_session_id = _create_session(client, owner_token)

    response = get_json(client, f"/session/get/{owner_session_id}", thief_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_analyst_can_delete_dm_session(client: TestClient):
    """Analyst can delete a DM's session."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_del", "dm_del")
    dm_token = login(client, username="dm_del", password="dm_del")  # noqa: S106

    dm_session_id = _create_session(client, dm_token)

    response = client.delete(
        f"/session/{dm_session_id}",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Confirm it's gone
    response = get_json(client, f"/session/get/{dm_session_id}", analyst_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_dm_cannot_delete_other_dm_session(client: TestClient):
    """DM cannot delete another DM's session (regression: latent ownership bug)."""
    analyst_token = login(client)
    _add_dm(client, analyst_token, "dm_keep", "dm_keep")
    _add_dm(client, analyst_token, "dm_attacker", "dm_attacker")

    keep_token = login(client, username="dm_keep", password="dm_keep")  # noqa: S106
    attacker_token = login(client, username="dm_attacker", password="dm_attacker")  # noqa: S106

    target_session_id = _create_session(client, keep_token)

    response = client.delete(
        f"/session/{target_session_id}",
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Session should still exist
    response = get_json(client, f"/session/get/{target_session_id}", analyst_token)
    assert response.status_code == status.HTTP_200_OK
