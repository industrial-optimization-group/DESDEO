"""Tests related to the SQLModels."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from desdeo.api.app import app
from desdeo.api.models import ConstantDB, ProblemDB, TensorConstantDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.schema import Constant, TensorConstant


@pytest.fixture(name="session_and_users")
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

        users = [user_analyst]

        yield {"session": session, "users": users}


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a client for testing."""
    client = TestClient(app)

    yield client


def test_tensor_constant(session_and_users: dict[str, Session | list[User]]):
    """Test that a tensor constant can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    t_tensor = TensorConstant(name="tensor", symbol="T", shape=[2, 2], values=[[1, 2], [3, 4]])
    t_tensor_dump = t_tensor.model_dump()
    t_tensor_dump["problem_id"] = 1

    db_tensor = TensorConstantDB.model_validate(t_tensor_dump)

    session.add(db_tensor)
    session.commit()

    statement = select(TensorConstantDB).where(TensorConstantDB.problem_id == 1)
    from_db_tensor = session.exec(statement).first()

    # check that original added TensorConstant and fetched match
    assert db_tensor == from_db_tensor

    from_db_tensor_dump = from_db_tensor.model_dump()
    t_tensor_validated = TensorConstant.model_validate(from_db_tensor_dump)

    assert t_tensor_validated == t_tensor


def test_constant(session_and_users: dict[str, Session | list[User]]):
    """Test that a scalar constant can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    constant = Constant(name="constant", symbol="c", value=69.420)
    constant_dump = constant.model_dump()
    constant_dump["problem_id"] = 1

    db_constant = ConstantDB.model_validate(constant_dump)

    session.add(db_constant)
    session.commit()

    statement = select(ConstantDB).where(ConstantDB.problem_id == 1)
    from_db_constant = session.exec(statement).first()

    assert db_constant == from_db_constant

    from_db_constant_dump = from_db_constant.model_dump()
    constant_validated = Constant.model_validate(from_db_constant_dump)

    assert constant_validated == constant


def test_problem(session_and_users: dict[str, Session | list[User]]):
    """Test that a problem can be added and fetched from the database correctly."""
    session = session_and_users["session"]
    user = session_and_users["users"][0]

    problemdb = ProblemDB(owner=user.id)
    session.add(problemdb)
    session.commit()
    session.refresh(problemdb)

    constant_1 = Constant(name="constant 1", symbol="c_1", value=69.420)
    constant_dump_1 = constant_1.model_dump()
    constant_dump_1["problem_id"] = problemdb.id

    db_constant_1 = ConstantDB.model_validate(constant_dump_1)

    constant_2 = Constant(name="constant 2", symbol="c_2", value=420.69)
    constant_dump_2 = constant_2.model_dump()
    constant_dump_2["problem_id"] = problemdb.id
    db_constant_2 = ConstantDB.model_validate(constant_dump_2)

    session.add(db_constant_1)
    session.add(db_constant_2)
    session.commit()

    statement = select(ConstantDB).where(ConstantDB.problem_id == problemdb.id)
    result = session.exec(statement).all()
