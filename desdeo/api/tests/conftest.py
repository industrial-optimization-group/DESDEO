"""General fixtures for API tests are defined here."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from desdeo.api.app import app
from desdeo.api.db import get_session
from desdeo.api.models import (
    ForestProblemMetaData,
    ProblemDB,
    ProblemMetaDataDB,
    User,
    UserRole,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dtlz2, river_pollution_problem, dmitry_forest_problem_disc


@pytest.fixture(name="session_and_user", scope="function")
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

        problem_db_river = ProblemDB.from_problem(river_pollution_problem(), user=user_analyst)
        session.add(problem_db_river)
        session.commit()
        session.refresh(problem_db_river)

        metadata = ProblemMetaDataDB(problem_id=problem_db_river.id)
        session.add(metadata)
        session.commit()
        session.refresh(metadata)

        forest_metadata = ForestProblemMetaData(
            metadata_id=metadata.id,
            map_json="type: string",
            schedule_dict={"type": "dict"},
            years=["type:", "list", "of", "strings"],
            stand_id_field="type: string",
        )

        session.add(forest_metadata)
        session.commit()

        problem_db_discrete = ProblemDB.from_problem(
            dmitry_forest_problem_disc(),
            user=user_analyst
        )
        session.add(problem_db_discrete)
        session.commit()
        session.refresh(problem_db_discrete)

        yield {"session": session, "user": user_analyst}
        session.rollback()


@pytest.fixture(name="client", scope="function")
def client_fixture(session_and_user):
    """Create a client for testing."""

    def get_session_override():
        return session_and_user["session"]

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()


def login(client: TestClient, username="analyst", password="analyst") -> str:  # noqa: S107
    """Login, returns the access token."""
    response_login = client.post(
        "/login",
        data={"username": username, "password": password, "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    ).json()

    return response_login["access_token"]


def post_json(client: TestClient, endpoint: str, json: dict, access_token: str):
    """Makes a post request and returns the response."""
    return client.post(
        endpoint,
        json=json,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )


def get_json(client: TestClient, endpoint: str, access_token: str):
    """Makes a get request and returns the response."""
    return client.get(
        endpoint,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
