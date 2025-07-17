"""General fixtures for API tests are defined here."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from desdeo.api.app import app
from desdeo.api.db import get_session
from desdeo.api.models import ProblemDB, User, UserRole, ProblemMetaDataDB, ForestProblemMetaData
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dtlz2, river_pollution_problem


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

        metadata = ProblemMetaDataDB(
        problem_id=problem_db_river.id,
        data = [
                ForestProblemMetaData(
                    map_json = "type: string",
                    schedule_dict = {"type": "dict"},
                    years = ["type:", "list", "of", "strings"],
                    stand_id_field = "type: string",
                ),
            ],
        )
        session.add(metadata)
        session.commit()
        session.refresh(metadata)

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
