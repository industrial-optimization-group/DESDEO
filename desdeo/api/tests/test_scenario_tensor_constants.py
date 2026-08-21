"""Tests that TensorConstants in scenario models survive the round trip through the API's DB models.

These cover the two places TensorConstants cross from `desdeo.tools.scenarios` into the SQLModel
layer: the raw scenario pool (`ScenarioModelDB`) and the merged/renamed constants produced by
`build_combined_scenario_problem` (`ProblemDB`). The latter exercises the fix in
`_build_constant_maps`/`_constant_value_key`, which made TensorConstant equality across scenario
leaves be judged by value instead of being silently skipped.
"""

# ruff: noqa: PLC0415 -- the fixture below imports lazily so the optional `web` extra / heavy deps
# are only pulled in when the fixture actually runs, matching the pattern in test_scenario_models.py.

import pytest
from sqlmodel import Session

from desdeo.api.models import ProblemDB, ScenarioModelDB, User
from desdeo.problem.scenario import Scenario, ScenarioModel
from desdeo.problem.schema import (
    Objective,
    ObjectiveTypeEnum,
    Problem,
    TensorConstant,
    Variable,
    VariableTypeEnum,
)
from desdeo.tools.scenarios import build_combined_scenario_problem


@pytest.fixture(name="session_and_user")
def session_fixture():
    """In-memory DB session with one analyst user and a base ProblemDB row."""
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


def _tensor_constant_scenario_model(shared_values, diff_values) -> ScenarioModel:
    """Build a two-leaf ScenarioModel pool with a shared and a per-leaf TensorConstant.

    ``t_shared`` is given ``shared_values`` in both leaves; ``t_diff`` is given
    ``diff_values[0]`` in ``s_1`` and ``diff_values[1]`` in ``s_2``.
    """
    base_problem = Problem(
        name="TensorConstant test problem",
        description="Minimal base problem for TensorConstant/API model tests.",
        variables=[
            Variable(
                name="x_1",
                symbol="x_1",
                lowerbound=-10,
                upperbound=10,
                initial_value=0,
                variable_type=VariableTypeEnum.real,
            ),
        ],
        objectives=[
            Objective(
                name="f_1",
                symbol="f_1",
                func="x_1",
                maximize=False,
                ideal=-100,
                nadir=100,
                objective_type=ObjectiveTypeEnum.analytical,
                is_linear=True,
                is_convex=True,
                is_twice_differentiable=True,
            ),
        ],
    )

    return ScenarioModel(
        scenario_tree={"ROOT": ["s_1", "s_2"], "s_1": [], "s_2": []},
        base_problem=base_problem,
        constants=[
            TensorConstant(name="t_shared (s_1)", symbol="t_shared", shape=[2], values=shared_values),  # index 0
            TensorConstant(name="t_shared (s_2)", symbol="t_shared", shape=[2], values=shared_values),  # index 1
            TensorConstant(name="t_diff (s_1)", symbol="t_diff", shape=[2], values=diff_values[0]),  # index 2
            TensorConstant(name="t_diff (s_2)", symbol="t_diff", shape=[2], values=diff_values[1]),  # index 3
        ],
        scenarios={
            "s_1": Scenario(constants={"t_shared": 0, "t_diff": 2}),
            "s_2": Scenario(constants={"t_shared": 1, "t_diff": 3}),
        },
    )


def test_scenario_model_db_round_trip_tensor_constant_pool(session_and_user):
    """ScenarioModelDB round-trips a pool of TensorConstants (incl. duplicate symbols) unchanged."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_db = session_and_user["problem_db"]

    original = _tensor_constant_scenario_model(shared_values=[1, 2], diff_values=([1, 2], [3, 4]))

    db_record = ScenarioModelDB.from_scenario_model(original, user=user, base_problem_id=problem_db.id)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)

    from_db = session.get(ScenarioModelDB, db_record.id)
    reconstructed = from_db.to_scenario_model(original.base_problem)

    orig_by_name = {c.name: c.get_values() for c in original.constants}
    rec_by_name = {c.name: c.get_values() for c in reconstructed.constants if isinstance(c, TensorConstant)}
    assert rec_by_name == orig_by_name


def test_combined_scenario_problem_tensor_constants_round_trip_through_problemdb(session_and_user):
    """The combined Problem's merged/renamed TensorConstants survive ProblemDB storage and retrieval.

    ``t_shared`` has equal values in both leaves so it should stay a single constant named
    ``t_shared``; ``t_diff`` differs per leaf so it should come out as ``s_1_t_diff``/``s_2_t_diff``.
    Both must persist through ``ProblemDB`` and reload with the correct per-symbol values.
    """
    session = session_and_user["session"]
    user = session_and_user["user"]

    model = _tensor_constant_scenario_model(shared_values=[1, 2], diff_values=([1, 2], [3, 4]))
    combined, _ = build_combined_scenario_problem(model)

    problem_db = ProblemDB.from_problem(combined, user=user)
    session.add(problem_db)
    session.commit()
    session.refresh(problem_db)

    from_db = session.get(ProblemDB, problem_db.id)
    reconstructed = Problem.from_problemdb(from_db)

    def value_map(problem: Problem) -> dict:
        return {
            c.symbol: c.get_values() if isinstance(c, TensorConstant) else c.value for c in (problem.constants or [])
        }

    orig_map = value_map(combined)
    rec_map = value_map(reconstructed)

    assert rec_map == orig_map
    assert rec_map.keys() == {"t_shared", "s_1_t_diff", "s_2_t_diff"}
    assert rec_map["t_shared"] == [1, 2]
    assert rec_map["s_1_t_diff"] == [1, 2]
    assert rec_map["s_2_t_diff"] == [3, 4]
