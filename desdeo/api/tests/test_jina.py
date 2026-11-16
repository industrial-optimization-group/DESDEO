"""Tests for the JINA endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from desdeo.api.app import app
from desdeo.api.db import get_session
from desdeo.api.models import (
    Group,
    JinaSetupState,
    ProblemDB,
    ProblemMetaDataDB,
    RepresentativeNonDominatedSolutions,
    ScenarioModelDB,
    SolverSelectionMetadata,
    StateDB,
    User,
    UserRole,
)
from desdeo.api.routers import jina as jina_router
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.api.tests.conftest import get_json, login, post_json
from desdeo.api.tests.test_routes import _setup_simple_scenario
from desdeo.mcdm.jina import Target, objective_ranges
from desdeo.problem import Constant
from desdeo.problem.scenario import ScenarioModel
from desdeo.problem.testproblems import simple_scenario_model, summer_cabin_battery_problem_split_scenario
from desdeo.tools import GurobipySolver
from desdeo.tools.robustness_metrics import domain_criterion
from desdeo.tools.scenario_designs import evaluate_design

pytestmark = [pytest.mark.api, pytest.mark.scenario]

URL = "/method/jina"


@pytest.fixture(name="client")
def jina_client_fixture(session_and_user):
    """A client whose requests each get a fresh database session, as in production."""
    engine = session_and_user["session"].get_bind()

    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    jina_router._cache.clear()
    jina_router._key_locks.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _stress_model() -> ScenarioModel:
    """Return the simple scenario model with two leaves t_1 and t_2 built like s_1 and s_3, with shifted c_1."""
    sm = simple_scenario_model()
    n = len(sm.constants)
    constants = [
        *sm.constants,
        Constant(name="c_1 (t_1)", symbol="c_1", value=2.0),
        Constant(name="c_1 (t_2)", symbol="c_1", value=7.0),
    ]
    scenarios = {
        "t_1": sm.scenarios["s_1"].model_copy(update={"constants": {"c_1": n}}),
        "t_2": sm.scenarios["s_3"].model_copy(update={"constants": {"c_1": n + 1}}),
    }
    fields = {name: getattr(sm, name) for name in type(sm).model_fields}
    return ScenarioModel(
        **fields
        | {
            "constants": constants,
            "scenarios": scenarios,
            "scenario_tree": {"ROOT": ["t_1", "t_2"], "t_1": [], "t_2": []},
            "scenario_probabilities": {"t_1": 0.5, "t_2": 0.5},
        }
    )


def _seed(session_and_user: dict) -> dict:
    """Store the simple scenario problem with a second scenario model, Gurobi as its solver and a solution set."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    problem_id, sm_id = _setup_simple_scenario(session_and_user)

    stress_db = ScenarioModelDB.from_scenario_model(_stress_model(), user=user, base_problem_id=problem_id)
    session.add(stress_db)
    metadata = ProblemMetaDataDB(problem_id=problem_id)
    session.add(metadata)
    session.commit()
    session.refresh(stress_db)
    session.refresh(metadata)

    session.add(SolverSelectionMetadata(metadata_id=metadata.id, solver_string_representation="gurobipy"))
    solutions = RepresentativeNonDominatedSolutions(
        metadata_id=metadata.id,
        name="Imported designs",
        solution_data={"x_1": [0.5, 0.8, 0.5, 2.0], "x_2": [1.0, 1.0, 1.0, 1.0]},
        ideal={},
        nadir={},
    )
    session.add(solutions)
    session.commit()
    session.refresh(solutions)
    return {"problem_id": problem_id, "sm_id": sm_id, "stress_id": stress_db.id, "solutions_id": solutions.id}


def _status(client: TestClient, token: str, state_id: int) -> dict:
    response = get_json(client, f"{URL}/status/{state_id}", token)
    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["is_ready"], body
    assert body["error"] is None, body["error"]
    return body


def _post_ready(client: TestClient, token: str, endpoint: str, json: dict) -> dict:
    """Post to an endpoint creating a state; return the finished state's status."""
    response = post_json(client, f"{URL}/{endpoint}", json, token)
    assert response.status_code == status.HTTP_200_OK, response.text
    return _status(client, token, response.json()["state_id"])


def _midpoint(ranges: dict[str, list[float]]) -> dict[str, float]:
    return {sym: (ideal + nadir) / 2 for sym, (ideal, nadir) in ranges.items()}


def _setup(client: TestClient, token: str, problem_id: int, **kwargs) -> dict:
    return _post_ready(client, token, "setup", {"problem_id": problem_id, **kwargs})


def _objective_ranges(setup_result: dict) -> dict[str, tuple[float, float]]:
    """Return the setup's per-scenario target ranges combined per objective."""
    targets = [Target.model_validate(t) for t in setup_result["targets"]["per_scenario"]]
    return objective_ranges(targets, {sym: tuple(r) for sym, r in setup_result["ranges"]["per_scenario"].items()})


def _assert_oracle(evaluated: dict, model: ScenarioModel, designs: dict, ranges: dict) -> None:
    """Assert that an evaluate state matches a direct evaluation at its thresholds and stores its domain criterion."""
    thresholds = evaluated["thresholds"]
    for design_id, leaves in evaluated["outcomes"].items():
        direct = evaluate_design(
            model, designs[int(design_id)]["values"], GurobipySolver, reference_point=thresholds, ranges=ranges
        )
        assert set(leaves) == set(direct)
        for leaf, outcome in direct.items():
            assert leaves[leaf]["status"] == outcome.status
            assert leaves[leaf]["objectives"] == pytest.approx(outcome.objectives, abs=1e-6)
    values = {
        design_id: {leaf: outcome["objectives"] for leaf, outcome in leaves.items() if outcome["status"]}
        for design_id, leaves in evaluated["outcomes"].items()
    }
    maximize = {obj.symbol: obj.maximize for obj in [*model.objectives, *model.base_problem.objectives]}
    expected = domain_criterion(values, maximize, thresholds)
    assert evaluated["domain_criterion"] == {design_id: dc.model_dump() for design_id, dc in expected.items()}


def test_scenario_models(client: TestClient, session_and_user: dict, monkeypatch: pytest.MonkeyPatch):
    """The scenario models of a problem are listed with their leaves, and their ids are on the problem info."""
    seeded = _seed(session_and_user)
    token = login(client)

    response = get_json(client, f"{URL}/scenario-models?problem_id={seeded['problem_id']}", token)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "id": seeded["sm_id"],
            "leaves": ["s_1", "s_2", "s_3"],
            "n_leaves": 3,
            "has_probabilities": True,
            "root_variables": ["x_1"],
            "default_design_variables": ["x_1"],
            "objectives": ["f_3", "f_1", "f_2"],
            "maximize": {"f_1": False, "f_2": False, "f_3": False},
        },
        {
            "id": seeded["stress_id"],
            "leaves": ["t_1", "t_2"],
            "n_leaves": 2,
            "has_probabilities": True,
            "root_variables": ["x_1"],
            "default_design_variables": ["x_1"],
            "objectives": ["f_3", "f_1", "f_2"],
            "maximize": {"f_1": False, "f_2": False, "f_3": False},
        },
    ]

    # A scenario model that fails to load is left out.
    load = jina_router.load_scenario_model

    def failing_load(scenario_model_id: int, db_session: Session) -> ScenarioModel | None:
        if scenario_model_id == seeded["stress_id"]:
            raise ValueError("broken")
        return load(scenario_model_id, db_session)

    monkeypatch.setattr(jina_router, "load_scenario_model", failing_load)
    response = get_json(client, f"{URL}/scenario-models?problem_id={seeded['problem_id']}", token)
    assert [info["id"] for info in response.json()] == [seeded["sm_id"]]
    monkeypatch.undo()

    info = get_json(client, f"/problem/{seeded['problem_id']}", token).json()
    assert info["scenario_model_ids"] == [seeded["sm_id"], seeded["stress_id"]]
    small = {p["id"]: p for p in get_json(client, "/problem/all", token).json()}
    assert small[seeded["problem_id"]]["scenario_model_ids"] == [seeded["sm_id"], seeded["stress_id"]]
    assert small[1]["scenario_model_ids"] == []


@pytest.mark.gurobipy
def test_jina_flow(client: TestClient, session_and_user: dict):
    """Setup, solve in both views, pool, import, evaluate, stress test, select, antifragility and designs listing."""
    seeded = _seed(session_and_user)
    problem_id = seeded["problem_id"]
    token = login(client)

    response = post_json(client, f"{URL}/get-or-initialize", {"problem_id": problem_id}, token)
    assert response.json() == {"setup": None, "states": []}

    setup = _setup(client, token, problem_id)
    setup_id = setup["state_id"]
    result = setup["result"]
    assert result["scenario_model_id"] == seeded["sm_id"]
    assert result["design_variables"] == ["x_1"]
    assert set(result["ranges"]) == {"aggregated", "per_scenario"}
    for view in ["aggregated", "per_scenario"]:
        assert set(result["ranges"][view]) == {t["symbol"] for t in result["targets"][view]}
    assert set(result["ranges"]["aggregated"]) == {"robust_f_3", "robust_f_1", "robust_f_2"}
    assert len(result["ranges"]["per_scenario"]) == 9

    # Aggregated worst case; the same reference point again only finds known designs.
    aggregated_rp = _midpoint(result["ranges"]["aggregated"])
    request = {"problem_id": problem_id, "setup_state_id": setup_id, "view": "aggregated"}
    first = _post_ready(client, token, "iterate", request | {"reference_point": aggregated_rp})["result"]
    assert [r["name"] for r in first["results"]] == ["balanced", "emphasis_f_3", "emphasis_f_1", "emphasis_f_2"]
    assert all(r["success"] for r in first["results"])
    assert first["new_design_ids"] == [d["id"] for d in first["designs"]]
    assert first["new_design_ids"][0] == 1
    assert {r["design_id"] for r in first["results"]} == set(first["new_design_ids"])
    again = _post_ready(client, token, "iterate", request | {"reference_point": aggregated_rp})["result"]
    assert again["new_design_ids"] == []
    assert [r["design_id"] for r in again["results"]] == [r["design_id"] for r in first["results"]]

    per_scenario_rp = _midpoint(result["ranges"]["per_scenario"])
    per_scenario = _post_ready(
        client, token, "iterate", request | {"view": "per_scenario", "reference_point": per_scenario_rp}
    )["result"]
    assert all(r["success"] for r in per_scenario["results"])
    assert all(d["view"] == "per_scenario" and d["source"] == "solve" for d in per_scenario["designs"])
    solved_ids = {r["design_id"] for r in first["results"] + per_scenario["results"]}

    # Pool mode never picks a design twice.
    picked: list[int] = []
    while True:
        pool = _post_ready(client, token, "iterate", request | {"mode": "pool", "reference_point": aggregated_rp})
        ids = {r["design_id"] for r in pool["result"]["results"]}
        if not ids:
            break
        assert not ids & set(picked)
        assert all(r["target_values"] for r in pool["result"]["results"])
        picked += ids
    assert set(picked) == solved_ids

    # Import: the third row repeats the first, and the fourth is infeasible in s_2 (con_4 needs x_1 <= 1).
    import_rp = {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}
    imported = _post_ready(
        client,
        token,
        "import",
        {
            "problem_id": problem_id,
            "setup_state_id": setup_id,
            "representative_set_id": seeded["solutions_id"],
            "reference_point": import_rp,
        },
    )["result"]
    assert imported["mode"] == "import"
    assert [d["values"] for d in imported["designs"]] == [{"x_1": 0.5}, {"x_1": 0.8}, {"x_1": 2.0}]
    assert all(d["source"] == "import" and d["effective_reference_point"] is None for d in imported["designs"])
    assert all(d["import_reference_point"] == import_rp for d in imported["designs"])
    assert [set(d["leaf_objectives"]) for d in imported["designs"]] == [{"s_1", "s_2", "s_3"}] * 2 + [{"s_1", "s_3"}]
    new_ids = imported["new_design_ids"]
    assert [r["design_id"] for r in imported["results"]] == [new_ids[0], new_ids[1], new_ids[0], new_ids[2]]
    assert [r["success"] for r in imported["results"]] == [True, True, True, False]
    assert "s_2" in imported["results"][3]["message"]
    imported_id = new_ids[0]

    designs_url = f"{URL}/designs?problem_id={problem_id}&setup_state_id={setup_id}"
    designs = {d["id"]: d for d in get_json(client, designs_url, token).json()}
    assert sorted(designs) == list(range(1, len(designs) + 1))
    assert all(set(d["target_values"]) == {"aggregated", "per_scenario"} for d in designs.values())
    assert set(designs[1]["target_values"]["aggregated"]) == {"robust_f_3", "robust_f_1", "robust_f_2"}

    # Evaluate every design in every leaf at the thresholds, with the design variables fixed.
    ranges = _objective_ranges(result)
    thresholds = _midpoint(ranges)
    evaluate_request = {"problem_id": problem_id, "setup_state_id": setup_id}
    for bad, named in [({"f_1": 0.0, "f_2": 0.0}, "f_3"), (thresholds | {"nope": 0.0}, "nope")]:
        response = post_json(client, f"{URL}/evaluate", evaluate_request | {"thresholds": bad}, token)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert named in response.json()["detail"]
    response = post_json(client, f"{URL}/evaluate", evaluate_request, token)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    evaluated = _post_ready(client, token, "evaluate", evaluate_request | {"thresholds": thresholds})
    evaluate_id = evaluated["state_id"]
    assert evaluated["result"]["thresholds"] == thresholds
    assert set(evaluated["result"]["outcomes"]) == {str(i) for i in designs}
    assert not all(outcome["status"] for outcome in evaluated["result"]["outcomes"][str(new_ids[2])].values())
    _assert_oracle(evaluated["result"], simple_scenario_model(), designs, ranges)

    # Stress test in the second scenario model at the same thresholds.
    stress = _post_ready(
        client,
        token,
        "evaluate",
        evaluate_request
        | {"scenario_model_id": seeded["stress_id"], "design_ids": [1, imported_id], "thresholds": thresholds},
    )["result"]
    assert stress["scenario_model_id"] == seeded["stress_id"]
    assert set(stress["outcomes"]["1"]) == {"t_1", "t_2"}
    _assert_oracle(stress, _stress_model(), designs, ranges)

    # Select.
    selected = _post_ready(
        client,
        token,
        "select",
        {"problem_id": problem_id, "setup_state_id": setup_id, "wishlist": [1, 2], "final_design_id": 2},
    )
    assert selected["kind"] == "jina.select"
    assert selected["result"] == {
        "kind": "jina.select",
        "setup_state_id": setup_id,
        "wishlist": [1, 2],
        "final_design_id": 2,
    }
    response = post_json(
        client, f"{URL}/select", {"problem_id": problem_id, "setup_state_id": setup_id, "wishlist": [999]}, token
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Antifragility needs a baseline leaf, and the analysis endpoint is gone.
    antifragility_request = {
        "problem_id": problem_id,
        "setup_state_id": setup_id,
        "evaluate_state_id": evaluate_id,
        "design_ids": [1, 2, 3],
    }
    response = post_json(client, f"{URL}/antifragility", antifragility_request, token)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "baseline" in response.json()["detail"]
    response = post_json(client, f"{URL}/analysis", antifragility_request, token)
    assert response.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED)

    # Restoring the session returns the setup and its later states in order.
    restored = post_json(client, f"{URL}/get-or-initialize", {"problem_id": problem_id}, token).json()
    assert restored["setup"]["state_id"] == setup_id
    state_ids = [s["state_id"] for s in restored["states"]]
    assert state_ids == sorted(state_ids)
    assert [s["kind"] for s in restored["states"]][-1] == "jina.select"
    assert evaluate_id in state_ids


@pytest.mark.gurobipy
def test_antifragility_with_baseline(client: TestClient, session_and_user: dict):
    """With a baseline leaf, the antifragility of evaluated designs is computed."""
    seeded = _seed(session_and_user)
    problem_id = seeded["problem_id"]
    token = login(client)

    setup = _setup(client, token, problem_id, baseline_leaf="s_1", measure="expected_value")
    assert setup["result"]["targets"]["aggregated"][0]["symbol"] == "E_f_3"
    request = {"problem_id": problem_id, "setup_state_id": setup["state_id"]}
    rp = _midpoint(setup["result"]["ranges"]["aggregated"])
    _post_ready(client, token, "iterate", request | {"reference_point": rp})
    thresholds = _midpoint(_objective_ranges(setup["result"]))
    evaluated = _post_ready(client, token, "evaluate", request | {"thresholds": thresholds})
    evaluate_id = evaluated["state_id"]

    response = post_json(client, f"{URL}/antifragility", request | {"evaluate_state_id": evaluate_id}, token)
    assert response.status_code == status.HTTP_200_OK, response.text
    analysis = response.json()
    assert set(analysis["antifragility"]) == set(evaluated["result"]["outcomes"])
    assert set(analysis["antifragility"]["1"]["objectives"]) == {"f_1", "f_2", "f_3"}
    assert isinstance(analysis["antifragile_objectives"], list)
    assert all(
        summary["taleb_class"] is None
        for result in analysis["antifragility"].values()
        for summary in result["objectives"].values()
    )

    # All objectives are minimised, so loose absolute floors breach nothing.
    summaries = {
        (design_id, obj): summary
        for design_id, result in analysis["antifragility"].items()
        for obj, summary in result["objectives"].items()
    }
    loose = {
        obj: max(s["worst_outcome"] for (_, o), s in summaries.items() if o == obj) + 1.0
        for obj in ("f_1", "f_2", "f_3")
    }
    analysis_request = request | {"evaluate_state_id": evaluate_id, "absolute_floors": loose}
    response = post_json(client, f"{URL}/antifragility", analysis_request, token)
    assert response.status_code == status.HTTP_200_OK, response.text
    floored = response.json()["antifragility"]
    for (design_id, obj), summary in summaries.items():
        expected = "antifragile" if summary["n_gain"] > 0 else "robust"
        assert floored[design_id]["objectives"][obj]["taleb_class"] == expected

    # A loss floor below a design's largest loss makes it fragile in that objective.
    (design_id, obj), summary = next(((key, s) for key, s in summaries.items() if s["max_loss_raw"] > 0))
    loss_floors = {obj: summary["max_loss_raw"] / 2}
    response = post_json(client, f"{URL}/antifragility", analysis_request | {"loss_floors": loss_floors}, token)
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()["antifragility"][design_id]["objectives"][obj]["taleb_class"] == "fragile"

    for floors in ("absolute_floors", "loss_floors"):
        response = post_json(client, f"{URL}/antifragility", analysis_request | {floors: {"nope": 1.0}}, token)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # The leaves of the stress model do not include the baseline leaf.
    stress = _post_ready(
        client,
        token,
        "evaluate",
        request | {"scenario_model_id": seeded["stress_id"], "thresholds": thresholds},
    )
    response = post_json(client, f"{URL}/antifragility", request | {"evaluate_state_id": stress["state_id"]}, token)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "baseline" in response.json()["detail"]


def _add_dm(session: Session, username: str) -> User:
    dm = User(username=username, password_hash=get_password_hash(username), role=UserRole.dm, group="test")
    session.add(dm)
    session.commit()
    session.refresh(dm)
    return dm


def test_status_errors(client: TestClient, session_and_user: dict):
    """Status is 404 for unknown and non-JINA states and for a state the user may not access."""
    seeded = _seed(session_and_user)
    session = session_and_user["session"]
    token = login(client)

    assert get_json(client, f"{URL}/status/99999", token).status_code == status.HTTP_404_NOT_FOUND
    response = post_json(
        client, "/method/cumulus/objective-constraint", {"problem_id": 1, "hard_constraints": []}, token
    )
    other_id = response.json()["state_id"]
    assert get_json(client, f"{URL}/status/{other_id}", token).status_code == status.HTTP_404_NOT_FOUND

    response = post_json(client, f"{URL}/setup", {"problem_id": seeded["problem_id"]}, token)
    setup_id = response.json()["state_id"]
    _add_dm(session, "dm")
    dm_token = login(client, "dm", "dm")
    assert get_json(client, f"{URL}/status/{setup_id}", dm_token).status_code == status.HTTP_404_NOT_FOUND


def _new_session(client: TestClient, token: str) -> int:
    """Create an interactive session, which becomes the user's active session."""
    response = post_json(client, "/session/new", {}, token)
    assert response.status_code == status.HTTP_200_OK, response.text
    return response.json()["id"]


def _restored_setup(client: TestClient, token: str, problem_id: int, **kwargs) -> int | None:
    response = post_json(client, f"{URL}/get-or-initialize", {"problem_id": problem_id} | kwargs, token)
    assert response.status_code == status.HTTP_200_OK, response.text
    setup = response.json()["setup"]
    return setup["state_id"] if setup is not None else None


def test_setup_access(client: TestClient, session_and_user: dict):
    """A setup is accessible like any state: in its owner's sessions, to analysts, and sessionless by problem."""
    seeded = _seed(session_and_user)
    session = session_and_user["session"]
    problem_id = seeded["problem_id"]
    analyst_token = login(client)
    owner = _add_dm(session, "owner")
    other = _add_dm(session, "other")
    group = Group(name="g", owner_id=session_and_user["user"].id, user_ids=[owner.id, other.id], problem_id=problem_id)
    session.add(group)
    session.commit()
    owner_token = login(client, "owner", "owner")
    other_token = login(client, "other", "other")

    def select(token: str, setup_id: int) -> int:
        request = {"problem_id": problem_id, "setup_state_id": setup_id, "wishlist": []}
        return post_json(client, f"{URL}/select", request, token).status_code

    first_session = _new_session(client, owner_token)
    setup_id = post_json(client, f"{URL}/setup", {"problem_id": problem_id}, owner_token).json()["state_id"]
    assert select(owner_token, setup_id) == status.HTTP_200_OK
    assert _restored_setup(client, owner_token, problem_id) == setup_id

    # get-or-initialize is scoped to the session; the owner's states stay usable from other sessions.
    _new_session(client, owner_token)
    assert _restored_setup(client, owner_token, problem_id) is None
    assert _restored_setup(client, owner_token, problem_id, session_id=first_session) == setup_id
    assert select(owner_token, setup_id) == status.HTTP_200_OK

    # Analysts may use any state and session.
    assert select(analyst_token, setup_id) == status.HTTP_200_OK
    assert _restored_setup(client, analyst_token, problem_id, session_id=first_session) == setup_id

    # Another DM of the problem may not use a state in the owner's session, nor name that session.
    _new_session(client, other_token)
    assert select(other_token, setup_id) == status.HTTP_404_NOT_FOUND
    assert get_json(client, f"{URL}/status/{setup_id}", other_token).status_code == status.HTTP_404_NOT_FOUND
    designs_url = f"{URL}/designs?problem_id={problem_id}&setup_state_id={setup_id}"
    assert get_json(client, designs_url, other_token).status_code == status.HTTP_404_NOT_FOUND
    assert _restored_setup(client, other_token, problem_id) is None
    response = post_json(
        client, f"{URL}/get-or-initialize", {"problem_id": problem_id, "session_id": first_session}, other_token
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # A state outside any session is accessible to the users of its problem.
    with Session(session.get_bind()) as fresh:
        for user_id in (owner.id, other.id):
            user = fresh.get(User, user_id)
            user.active_session_id = None
            fresh.add(user)
        fresh.commit()
    sessionless_id = post_json(client, f"{URL}/setup", {"problem_id": problem_id}, owner_token).json()["state_id"]
    assert select(other_token, sessionless_id) == status.HTTP_200_OK
    assert _restored_setup(client, other_token, problem_id) == sessionless_id


@pytest.mark.gurobipy
def test_lineage(client: TestClient, session_and_user: dict):
    """JINA states descend from their setup unless a parent state is given."""
    seeded = _seed(session_and_user)
    engine = session_and_user["session"].get_bind()
    problem_id = seeded["problem_id"]
    token = login(client)
    _new_session(client, token)
    post_json(client, "/method/cumulus/objective-constraint", {"problem_id": problem_id}, token)

    setup = _setup(client, token, problem_id)
    setup_id = setup["state_id"]
    rp = _midpoint(setup["result"]["ranges"]["aggregated"])
    request = {"problem_id": problem_id, "setup_state_id": setup_id, "mode": "pool", "reference_point": rp}
    first = _post_ready(client, token, "iterate", request)["state_id"]
    second = _post_ready(client, token, "iterate", request)["state_id"]
    third = _post_ready(client, token, "iterate", request | {"parent_state_id": first})["state_id"]

    with Session(engine) as fresh:
        parents = {state_id: fresh.get(StateDB, state_id).parent_id for state_id in [setup_id, first, second, third]}
    assert parents == {setup_id: None, first: setup_id, second: setup_id, third: first}


def test_background_failure(client: TestClient, session_and_user: dict, monkeypatch):
    """A background task that raises leaves its state ready with the error."""
    seeded = _seed(session_and_user)
    token = login(client)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(jina_router, "target_ranges", boom)
    response = post_json(client, f"{URL}/setup", {"problem_id": seeded["problem_id"]}, token)
    body = get_json(client, f"{URL}/status/{response.json()['state_id']}", token).json()
    assert body["is_ready"]
    assert body["error"] == "RuntimeError: boom"
    assert body["result"]["ranges"] is None


@pytest.mark.gurobipy
def test_iterate_failure(client: TestClient, session_and_user: dict, monkeypatch):
    """A solve that raises leaves the iterate state ready with the error and no designs."""
    seeded = _seed(session_and_user)
    problem_id = seeded["problem_id"]
    token = login(client)
    setup = _setup(client, token, problem_id)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(jina_router, "solve_variants", boom)
    rp = _midpoint(setup["result"]["ranges"]["aggregated"])
    request = {"problem_id": problem_id, "setup_state_id": setup["state_id"], "reference_point": rp}
    response = post_json(client, f"{URL}/iterate", request, token)
    body = get_json(client, f"{URL}/status/{response.json()['state_id']}", token).json()
    assert body["is_ready"]
    assert body["error"] == "RuntimeError: boom"
    assert body["result"]["designs"] == []


def test_cvar_maximize_setup(client: TestClient, session_and_user: dict):
    """A CVaR setup with a maximised objective computes its ranges."""
    session = session_and_user["session"]
    model = simple_scenario_model()
    f_3 = model.base_problem.objectives[0].model_copy(update={"func": ["Multiply", 1, "x_2"], "maximize": True})
    model = model.with_base_problem(model.base_problem.model_copy(update={"objectives": [f_3]}))
    max_db = ProblemDB.from_problem(model.base_problem, user=session_and_user["user"])
    session.add(max_db)
    session.commit()
    session.refresh(max_db)
    session.add(ScenarioModelDB.from_scenario_model(model, user=session_and_user["user"], base_problem_id=max_db.id))
    session.commit()
    token = login(client)

    result = _setup(client, token, max_db.id, measure="cvar")["result"]
    aggregated = result["targets"]["aggregated"]
    assert [t["maximize"] for t in aggregated] == [True, False, False]
    assert set(result["ranges"]["aggregated"]) == {t["symbol"] for t in aggregated}
    for t in aggregated:
        ideal, nadir = result["ranges"]["aggregated"][t["symbol"]]
        assert ideal >= nadir if t["maximize"] else ideal <= nadir


def test_invalid_inputs(client: TestClient, session_and_user: dict):
    """Invalid setups and iterations are rejected."""
    seeded = _seed(session_and_user)
    session = session_and_user["session"]
    problem_id = seeded["problem_id"]
    token = login(client)

    def setup_status(**kwargs) -> int:
        return post_json(client, f"{URL}/setup", {"problem_id": problem_id} | kwargs, token).status_code

    assert post_json(client, f"{URL}/setup", {"problem_id": 1}, token).status_code == 422
    assert setup_status(design_variables=["x_2"]) == 422
    assert setup_status(design_variables=[]) == 422
    assert setup_status(baseline_leaf="nope") == 422
    assert setup_status(measure="median") == 422
    assert setup_status(cvar_alpha=1.5) == 422
    for body in [
        f'{{"problem_id": {problem_id}, "cvar_alpha": NaN}}',
        f'{{"problem_id": {problem_id}, "setup_state_id": 1, "reference_point": {{"robust_f_1": Infinity}}}}',
    ]:
        endpoint = "setup" if "cvar_alpha" in body else "iterate"
        response = client.post(
            f"{URL}/{endpoint}",
            content=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        assert response.status_code == 422, body
    evaluate = f'{{"problem_id": {problem_id}, "setup_state_id": 1, "thresholds": {{"f_1": NaN}}}}'
    response = client.post(
        f"{URL}/evaluate",
        content=evaluate,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert response.status_code == 422

    other_id, foreign_id = _setup_simple_scenario(session_and_user)
    assert setup_status(scenario_model_id=foreign_id) == 422
    assert setup_status(scenario_model_id=99999) == 422

    # A setup whose ranges are not computed yet cannot be iterated.
    response = post_json(client, f"{URL}/setup", {"problem_id": other_id}, token)
    setup_id = response.json()["state_id"]
    with Session(session.get_bind()) as fresh:
        sub = fresh.get(JinaSetupState, fresh.get(StateDB, setup_id).state_id)
        sub.is_ready = False
        fresh.add(sub)
        fresh.commit()
    request = {"problem_id": other_id, "setup_state_id": setup_id, "reference_point": {"robust_f_1": 0.0}}
    assert post_json(client, f"{URL}/iterate", request, token).status_code == status.HTTP_409_CONFLICT

    # Iterating a setup of another problem.
    request = {"problem_id": problem_id, "setup_state_id": setup_id, "reference_point": {"robust_f_1": 0.0}}
    assert post_json(client, f"{URL}/iterate", request, token).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.gurobipy
def test_invalid_iterations(client: TestClient, session_and_user: dict):
    """Reference points with unknown targets, foreign solution sets and missing columns are rejected."""
    seeded = _seed(session_and_user)
    session = session_and_user["session"]
    problem_id = seeded["problem_id"]
    token = login(client)
    setup_id = _setup(client, token, problem_id)["state_id"]
    request = {"problem_id": problem_id, "setup_state_id": setup_id}

    assert post_json(client, f"{URL}/iterate", request | {"reference_point": {"f_1": 0.0}}, token).status_code == 422
    assert post_json(client, f"{URL}/iterate", request | {"reference_point": {}}, token).status_code == 422
    rp = {"s_1_f_1": 0.0}
    assert (
        post_json(
            client, f"{URL}/iterate", request | {"view": "per_scenario", "reference_point": rp}, token
        ).status_code
        == 200
    )
    assert (
        post_json(client, f"{URL}/iterate", request | {"view": "sideways", "reference_point": rp}, token).status_code
        == 422
    )

    import_request = request | {"reference_point": {"f_1": 0.0}}
    # The river pollution problem's solution set belongs to problem 2.
    assert post_json(client, f"{URL}/import", import_request | {"representative_set_id": 1}, token).status_code == 422
    metadata = session.get(ProblemDB, problem_id).problem_metadata
    session.add(
        RepresentativeNonDominatedSolutions(
            metadata_id=metadata.id, name="No designs", solution_data={"f_1": [1.0]}, ideal={}, nadir={}
        )
    )
    session.commit()
    response = post_json(client, f"{URL}/import", import_request | {"representative_set_id": 3}, token)
    assert response.status_code == 422
    assert "x_1" in response.json()["detail"]
    bad_rp = import_request | {"representative_set_id": seeded["solutions_id"], "reference_point": {"g": 0.0}}
    assert post_json(client, f"{URL}/import", bad_rp, token).status_code == 422

    evaluate_request = request | {"thresholds": {"f_1": 0.0, "f_2": 0.0, "f_3": 0.0}}
    response = post_json(client, f"{URL}/evaluate", evaluate_request | {"design_ids": [999]}, token)
    assert response.status_code == 422
    assert "999" in response.json()["detail"]
    _, foreign_id = _setup_simple_scenario(session_and_user)
    response = post_json(client, f"{URL}/evaluate", evaluate_request | {"scenario_model_id": foreign_id}, token)
    assert response.status_code == 422


@pytest.mark.slow
@pytest.mark.gurobipy
@pytest.mark.githubskip
def test_summer_cabin_smoke(client: TestClient, session_and_user: dict):
    """A setup and a worst-case iteration on the summer cabin give investment designs."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    model = summer_cabin_battery_problem_split_scenario()
    problem_db = ProblemDB.from_problem(model.base_problem, user=user)
    session.add(problem_db)
    session.commit()
    session.refresh(problem_db)
    session.add(ScenarioModelDB.from_scenario_model(model, user=user, base_problem_id=problem_db.id))
    metadata = ProblemMetaDataDB(problem_id=problem_db.id)
    session.add(metadata)
    session.commit()
    session.refresh(metadata)
    session.add(SolverSelectionMetadata(metadata_id=metadata.id, solver_string_representation="gurobipy"))
    session.commit()
    token = login(client)

    setup = _setup(client, token, problem_db.id)
    rp = _midpoint(setup["result"]["ranges"]["aggregated"])
    request = {"problem_id": problem_db.id, "setup_state_id": setup["state_id"], "reference_point": rp}
    result = _post_ready(client, token, "iterate", request)["result"]
    assert all(r["success"] for r in result["results"]), [r["message"] for r in result["results"]]
    root = {"y", "E", "n", "c_s1", "d_s1", "soc_s1", "buy_s1", "sell_s1"}
    assert all(set(d["values"]) == root for d in result["designs"])
