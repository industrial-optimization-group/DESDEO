"""Tests related to routes and routers."""

import asyncio
import time

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, WSGITransport
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from desdeo.api.app import app
from desdeo.api.db import get_session
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import create_access_token, get_password_hash
from desdeo.problem import dtlz2


@pytest.fixture(name="session", scope="session")
def session_fixture():
    """Create a session for testing."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user_analyst = User(
            username="analyst",
            password_hash=get_password_hash("analyst"),
            role=UserRole.analyst,
            group="test",
        )
        session.add(user_analyst)
        session.commit()
        session.refresh(user_analyst)

        problem_db = ProblemDB.from_problem(dtlz2(5, 3), user=user_analyst)
        session.add(problem_db)
        session.commit()
        session.refresh(problem_db)

        yield session
        session.rollback()


@pytest_asyncio.fixture(name="async_client", scope="function")
async def client_fixture(session: Session):
    """Client fixture."""

    def get_session_overdrive():
        return session

    app.dependency_overrides[get_session] = get_session_overdrive

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="client", scope="function")
def client_fixture_(session: Session):
    """Client fixture."""

    def get_session_overdrive():
        return session

    app.dependency_overrides[get_session] = get_session_overdrive

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


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
