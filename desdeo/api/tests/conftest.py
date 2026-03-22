"""General fixtures for API tests are defined here."""

import io
from pathlib import Path

import polars as pl
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
    RepresentativeNonDominatedSolutions,
    User,
    UserRole,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dmitry_forest_problem_disc, dtlz2, river_pollution_problem


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

        data_path = Path(__file__).parent.parent.parent.parent / "datasets" / "river_pollution_non_dom.parquet"
        df = pl.read_parquet(data_path)
        dict_data = df.to_dict(as_series=False)
        river_nondominated_meta = RepresentativeNonDominatedSolutions(
            metadata_id=metadata.id,
            name="Non-dom-solutions",
            description=(
                "Set of non-dominated solutions representing the Pareto optimal "
                "solutions of the river pollution problem."
            ),
            solution_data=dict_data,
            ideal={},
            nadir={},
        )

        session.add(river_nondominated_meta)
        session.commit()

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


def post_file_multipart(
    client: TestClient, endpoint: str, file_bytes: bytes, access_token: str, filename: str = "test.json"
):
    """Makes a post request with an uploaded file and returns the response."""
    return client.post(
        endpoint,
        files={"json_file": (filename, io.BytesIO(file_bytes), "application/json")},
        headers={"Authorization": f"Bearer {access_token}"},
    )


def get_json(client: TestClient, endpoint: str, access_token: str):
    """Makes a get request and returns the response."""
    return client.get(
        endpoint,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
