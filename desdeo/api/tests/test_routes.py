"""Tests related to routes and routers."""

from fastapi.testclient import TestClient

from desdeo.api.models import ProblemGetRequest, ProblemInfo
from desdeo.api.routers.user_authentication import (
    create_access_token,
)


def test_user_login(client: TestClient):
    """Test that login works."""
    response = client.post(
        "/login",
        data={"username": "analyst", "password": "analyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

    # wrong login
    response = client.post(
        "/login",
        data={"username": "analyst", "password": "anallyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401


def test_tokens():
    """Test token generation."""
    token_1 = create_access_token({"id": 1, "sub": "analyst"})
    token_2 = create_access_token({"id": 1, "sub": "analyst"})

    assert token_1 != token_2


def test_refresh(client: TestClient):
    """Test that refreshing the access token works."""
    # check that no previous cookies exist
    assert len(client.cookies) == 0

    # no cookie
    response_bad = client.post("/refresh")

    response_good = client.post(
        "/login",
        data={"username": "analyst", "password": "analyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response_bad.status_code == 401
    assert response_good.status_code == 200

    assert "access_token" in response_good.json()
    assert len(client.cookies) == 1
    assert "refresh_token" in client.cookies

    response_refresh = client.post("/refresh")

    assert "access_token" in response_refresh.json()

    assert response_good.json()["access_token"] != response_refresh.json()["access_token"]


def test_get_problem(client: TestClient):
    """Test fetching specific problems based on their id."""
    response_login = client.post(
        "/login",
        data={"username": "analyst", "password": "analyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    ).json()

    access_token = response_login["access_token"]

    response = client.post(
        "/problem/get",
        json=ProblemGetRequest(problem_id=1).model_dump(),
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200

    info = ProblemInfo.model_validate(response.json())

    assert info.id == 1
    assert info.name == "dtlz2"

    response = client.post(
        "/problem/get",
        json=ProblemGetRequest(problem_id=2).model_dump(),
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200

    info = ProblemInfo.model_validate(response.json())

    assert info.id == 2
    assert info.name == "The river pollution problem"
