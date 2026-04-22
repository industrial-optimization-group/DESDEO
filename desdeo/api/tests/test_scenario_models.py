"""Tests for ScenarioModelDB and ScenarioModelInfo."""

import pytest
from sqlmodel import Session

from desdeo.api.models import ProblemDB, ScenarioModelDB, ScenarioModelInfo, User
from desdeo.problem.testproblems import river_pollution_scenario, simple_scenario_model


@pytest.fixture(name="session_and_user")
def session_fixture():
    """In-memory DB session with one analyst user."""
    from sqlmodel import SQLModel, create_engine
    from sqlmodel.pool import StaticPool

    from desdeo.api.models import UserRole
    from desdeo.api.routers.user_authentication import get_password_hash
    from desdeo.problem.testproblems import dtlz2

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(
            username="analyst",
            password_hash=get_password_hash("analyst"),
            role=UserRole.analyst,
            group="test",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        problem_db = ProblemDB.from_problem(dtlz2(5, 3), user=user)
        session.add(problem_db)
        session.commit()
        session.refresh(problem_db)

        yield {"session": session, "user": user, "problem_db": problem_db}
        session.rollback()


def test_scenario_model_db_from_simple(session_and_user):
    """ScenarioModelDB can be created from simple_scenario_model and stored in the DB."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_db = session_and_user["problem_db"]

    model = simple_scenario_model()

    db_record = ScenarioModelDB.from_scenario_model(model, user=user, base_problem_id=problem_db.id)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)

    from_db = session.get(ScenarioModelDB, db_record.id)

    assert from_db is not None
    assert from_db.user_id == user.id
    assert from_db.base_problem_id == problem_db.id
    assert from_db.scenario_tree == model.scenario_tree
    assert set(from_db.scenarios.keys()) == set(model.scenarios.keys())
    assert from_db.anticipation_stop == model.anticipation_stop


def test_scenario_model_db_round_trip_simple(session_and_user):
    """ScenarioModelDB round-trips back to an equivalent ScenarioModel via to_scenario_model."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_db = session_and_user["problem_db"]

    original = simple_scenario_model()

    db_record = ScenarioModelDB.from_scenario_model(original, user=user, base_problem_id=problem_db.id)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)

    from_db = session.get(ScenarioModelDB, db_record.id)
    reconstructed = from_db.to_scenario_model(original.base_problem)

    assert reconstructed.scenario_tree == original.scenario_tree
    assert reconstructed.anticipation_stop == original.anticipation_stop
    assert set(reconstructed.scenarios.keys()) == set(original.scenarios.keys())

    for name in original.scenarios:
        assert reconstructed.scenarios[name] == original.scenarios[name]

    orig_obj_symbols = {o.symbol for o in original.objectives}
    rec_obj_symbols = {o.symbol for o in reconstructed.objectives}
    assert orig_obj_symbols == rec_obj_symbols

    orig_con_symbols = {c.symbol for c in original.constraints}
    rec_con_symbols = {c.symbol for c in reconstructed.constraints}
    assert orig_con_symbols == rec_con_symbols


def test_scenario_model_db_get_scenario_problem(session_and_user):
    """get_scenario_problem works correctly on a ScenarioModel reconstructed from the DB."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_db = session_and_user["problem_db"]

    original = simple_scenario_model()

    db_record = ScenarioModelDB.from_scenario_model(original, user=user, base_problem_id=problem_db.id)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)

    from_db = session.get(ScenarioModelDB, db_record.id)
    reconstructed = from_db.to_scenario_model(original.base_problem)

    for scenario_name in original.scenarios:
        p_original = original.get_scenario_problem(scenario_name)
        p_reconstructed = reconstructed.get_scenario_problem(scenario_name)

        assert {o.symbol for o in p_original.objectives} == {o.symbol for o in p_reconstructed.objectives}
        assert {c.symbol for c in p_original.constraints} == {c.symbol for c in p_reconstructed.constraints}


def test_scenario_model_db_round_trip_river_pollution(session_and_user):
    """ScenarioModelDB round-trips the river pollution scenario with 6 scenarios and pool objectives."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_db = session_and_user["problem_db"]

    original = river_pollution_scenario()

    db_record = ScenarioModelDB.from_scenario_model(original, user=user, base_problem_id=problem_db.id)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)

    from_db = session.get(ScenarioModelDB, db_record.id)
    reconstructed = from_db.to_scenario_model(original.base_problem)

    assert len(reconstructed.scenario_tree["ROOT"]) == 6
    assert set(reconstructed.scenarios.keys()) == set(original.scenarios.keys())
    assert len(reconstructed.objectives) == len(original.objectives)

    for i in range(1, 7):
        name = f"scenario_{i}"
        p = reconstructed.get_scenario_problem(name)
        assert len(p.objectives) == 4


def test_scenario_model_info_from_db(session_and_user):
    """ScenarioModelInfo can be constructed from a ScenarioModelDB row."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_db = session_and_user["problem_db"]

    original = simple_scenario_model()

    db_record = ScenarioModelDB.from_scenario_model(original, user=user, base_problem_id=problem_db.id)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)

    from_db = session.get(ScenarioModelDB, db_record.id)
    info = ScenarioModelInfo.model_validate(from_db, from_attributes=True)

    assert info.id == from_db.id
    assert info.user_id == user.id
    assert info.base_problem_id == problem_db.id
    assert info.scenario_tree == original.scenario_tree
    assert set(info.scenarios.keys()) == set(original.scenarios.keys())
