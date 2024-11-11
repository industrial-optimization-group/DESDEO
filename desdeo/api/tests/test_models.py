"""Tests related to the SQLModels."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from desdeo.api.app import app
from desdeo.api.models import (
    ConstantDB,
    ConstraintDB,
    DiscreteRepresentationDB,
    ExtraFunctionDB,
    ObjectiveDB,
    ProblemDB,
    ScalarizationFunctionDB,
    SimulatorDB,
    TensorConstantDB,
    TensorVariableDB,
    User,
    UserRole,
    VariableDB,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.schema import (
    Constant,
    Constraint,
    ConstraintTypeEnum,
    DiscreteRepresentation,
    ExtraFunction,
    Objective,
    ObjectiveTypeEnum,
    ScalarizationFunction,
    Simulator,
    TensorConstant,
    TensorVariable,
    Variable,
    VariableTypeEnum,
)
from desdeo.problem.testproblems import binh_and_korn


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


def test_variable(session_and_users: dict[str, Session | list[User]]):
    """Test that a scalar variable can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    variable = Variable(
        name="test variable",
        symbol="x_1",
        initial_value=69,
        lowerbound=42,
        upperbound=420,
        variable_type=VariableTypeEnum.integer,
    )

    variable_dump = variable.model_dump()
    variable_dump["problem_id"] = 1

    db_variable = VariableDB.model_validate(variable_dump)

    session.add(db_variable)
    session.commit()
    session.refresh(db_variable)

    from_db_variable = session.get(VariableDB, 1)

    assert db_variable == from_db_variable

    from_db_variable_dump = from_db_variable.model_dump()
    variable_validated = Variable.model_validate(from_db_variable_dump)

    assert variable_validated == variable


def test_tensor_variable(session_and_users: dict[str, Session | list[User]]):
    """Test that a tensor variable can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    t_variable = TensorVariable(
        name="test variable",
        symbol="X",
        shape=[2, 2],
        initial_values=[[1, 2], [3, 4]],
        lowerbounds=[[0, 1], [1, 0]],
        upperbounds=[[99, 89], [88, 77]],
        variable_type=VariableTypeEnum.integer,
    )

    t_variable_dump = t_variable.model_dump()
    t_variable_dump["problem_id"] = 69

    db_t_variable = TensorVariableDB.model_validate(t_variable_dump)

    session.add(db_t_variable)
    session.commit()
    session.refresh(db_t_variable)

    from_db_t_variable = session.get(TensorVariableDB, 1)

    assert db_t_variable == from_db_t_variable

    from_db_t_variable_dump = from_db_t_variable.model_dump()
    t_variable_validated = TensorVariable.model_validate(from_db_t_variable_dump)

    assert t_variable_validated == t_variable


def test_objective(session_and_users: dict[str, Session | list[User]]):
    """Test that an objective can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    objective = Objective(
        name="Test Objective",
        symbol="f_1",
        func="x_1 + x_2 + Sin(y)",
        objective_type=ObjectiveTypeEnum.analytical,
        ideal=10.5,
        nadir=20.0,
        maximize=False,
        scenario_keys=["s_1", "s_2"],
        unit="m",
        is_convex=False,
        is_linear=True,
        is_twice_differentiable=True,
        simulator_path="/dev/null",
        surrogates=["/var/log", "/dev/sda/sda1"],
    )

    objective_dump = objective.model_dump()
    objective_dump["problem_id"] = 420  # yes

    db_objective = ObjectiveDB.model_validate(objective_dump)

    session.add(db_objective)
    session.commit()
    session.refresh(db_objective)

    from_db_objective = session.get(ObjectiveDB, 1)

    assert db_objective == from_db_objective

    from_db_objective_dump = from_db_objective.model_dump()
    objective_validated = Objective.model_validate(from_db_objective_dump)

    assert objective_validated == objective


def test_constraint(session_and_users: dict[str, Session | list[User]]):
    """Test that an constraint can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    constraint = Constraint(
        name="Test Constraint",
        symbol="g_1",
        func="x_1 + x_1 + x_1 - 10",
        cons_type=ConstraintTypeEnum.LTE,
        is_convex=True,
        is_linear=False,
        is_twice_differentiable=False,
        scenario_keys=["Abloy", "MasterLock", "MasterLockToOpenMasterLock"],
        simulator_path="/dev/null/aaaaaaaaaa",
        surrogates=["/var/log", "/dev/sda/sda1/no"],
    )

    constraint_dump = constraint.model_dump()
    constraint_dump["problem_id"] = 72

    db_constraint = ConstraintDB.model_validate(constraint_dump)

    session.add(db_constraint)
    session.commit()
    session.refresh(db_constraint)

    from_db_constraint = session.get(ConstraintDB, 1)

    assert db_constraint == from_db_constraint

    from_db_constraint_dump = from_db_constraint.model_dump()
    constraint_validated = Constraint.model_validate(from_db_constraint_dump)

    assert constraint_validated == constraint


def test_scalarization_function(session_and_users: dict[str, Session | list[User]]):
    """Test that a scalarization function can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    scalarization = ScalarizationFunction(
        name="Test ScalarizationFunction",
        symbol="s_1",
        func="x_1 + x_1 + x_1 - 10 - 99999 + Sin(y_3)",
        is_convex=True,
        is_linear=True,
        is_twice_differentiable=False,
        scenario_keys=["Abloy", "MasterLock", "MasterLockToOpenMasterLock", "MyHandsHurt"],
    )

    scalarization_dump = scalarization.model_dump()
    scalarization_dump["problem_id"] = 2

    db_scalarization = ScalarizationFunctionDB.model_validate(scalarization_dump)

    session.add(db_scalarization)
    session.commit()
    session.refresh(db_scalarization)

    from_db_scalarization = session.get(ScalarizationFunctionDB, 1)

    assert db_scalarization == from_db_scalarization

    from_db_scalarization_dump = from_db_scalarization.model_dump()
    scalarization_validated = ScalarizationFunction.model_validate(from_db_scalarization_dump)

    assert scalarization_validated == scalarization


def test_extra_function(session_and_users: dict[str, Session | list[User]]):
    """Test that an extra function can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    extra = ExtraFunction(
        name="Test ExtraFunction",
        symbol="extra_1",
        func="x_1 + x_2 + x_9000 - 10 - 99999 + Cos(y_3)",
        is_convex=False,
        is_linear=False,
        is_twice_differentiable=True,
        scenario_keys=["Abloy", "MasterLock", "MasterLockToOpenMasterLock", "MyHandsHurt", "RunningOutOfIdeas"],
    )

    extra_dump = extra.model_dump()
    extra_dump["problem_id"] = 5

    db_extra = ExtraFunctionDB.model_validate(extra_dump)

    session.add(db_extra)
    session.commit()
    session.refresh(db_extra)

    from_db_extra = session.get(ExtraFunctionDB, 1)

    assert db_extra == from_db_extra

    from_db_extra_dump = from_db_extra.model_dump()
    extra_validated = ExtraFunction.model_validate(from_db_extra_dump)

    assert extra_validated == extra


def test_discrete_representation(session_and_users: dict[str, Session | list[User]]):
    """Test that a DiscreteRepresentation can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    discrete = DiscreteRepresentation(
        variable_values={"x_1": [1, 2, 3, 4, 5], "x_2": [6, 7, 8, 9, 10]},
        objective_values={"f_1": [0.5, 1.0, 2.0, 3.5, 9], "f_2": [-1, -2, -3, -4, -5]},
        non_dominated=True,
    )

    discrete_dump = discrete.model_dump()
    discrete_dump["problem_id"] = 3

    db_discrete = DiscreteRepresentationDB.model_validate(discrete_dump)

    session.add(db_discrete)
    session.commit()
    session.refresh(db_discrete)

    from_db_discrete = session.get(DiscreteRepresentationDB, 1)

    assert db_discrete == from_db_discrete

    from_db_discrete_dump = from_db_discrete.model_dump()
    discrete_validated = DiscreteRepresentation.model_validate(from_db_discrete_dump)

    assert discrete_validated == discrete


def test_simulator(session_and_users: dict[str, Session | list[User]]):
    """Test that a Simulator can be transformed to an SQLModel and back after adding it to the database."""
    session = session_and_users["session"]

    simulator = Simulator(
        file="/my/favorite/simulator.exe",
        name="simulator",
        symbol="simu",
        parameter_options={"param1": 69, "nice": True},
    )

    simulator_dump = simulator.model_dump()
    simulator_dump["problem_id"] = 2

    db_simulator = SimulatorDB.model_validate(simulator_dump)

    session.add(db_simulator)
    session.commit()
    session.refresh(db_simulator)

    from_db_simulator = session.get(SimulatorDB, 1)

    assert db_simulator == from_db_simulator

    from_db_simulator_dump = from_db_simulator.model_dump()
    simulator_validated = Simulator.model_validate(from_db_simulator_dump)

    assert simulator_validated == simulator


def test_from_pydantic(session_and_users: dict[str, Session | list[User]]):
    """Test that a problem can be added and fetched from the database correctly."""
    session = session_and_users["session"]
    user = session_and_users["users"][0]

    problem_binh = binh_and_korn()

    problemdb = ProblemDB.from_problem(problem_binh, user=user)
    session.add(problemdb)
    session.commit()
    session.refresh(problemdb)

    from_db_problem = session.get(ProblemDB, 1)

    assert problemdb == from_db_problem

    from_db_problem_dump = from_db_problem.model_dump()
    problem_validated = ProblemDB.model_validate(from_db_problem_dump)

    assert problem_validated == problemdb
