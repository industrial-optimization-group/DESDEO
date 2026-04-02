"""Tests for the site selection metadata and map endpoints."""

import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from desdeo.api.models import (
    ProblemDB,
    ProblemMetaDataDB,
    SiteSelectionMetaData,
    User,
    UserRole,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import river_pollution_problem

from .conftest import login, post_json

# --- Minimal synthetic data for tests ---

SITES = [
    {"name": "Library A", "node": "CityA", "lat": 40.0, "lon": -83.0},
    {"name": "Center B", "node": "CityA", "lat": 40.01, "lon": -83.01},
    {"name": "Clinic C", "node": "CityB", "lat": 40.1, "lon": -83.1},
]
NODES = [
    {"name": "CityA", "lat": 40.0, "lon": -83.0, "size": 10.0},
    {"name": "CityB", "lat": 40.1, "lon": -83.1, "size": 5.0},
]
TRAVEL_TIME_MATRIX = [
    [0.0, 10.0],
    [10.0, 0.0],
]
SITE_VARS = ["x_1", "x_2", "x_3"]
COVER_VARS = ["cover_1", "cover_2"]


# --- Model tests ---


def test_site_selection_metadata_create(session_and_user: dict):
    """Create a SiteSelectionMetaData instance and verify round-trip through DB."""
    session: Session = session_and_user["session"]

    problem = session.exec(select(ProblemDB)).first()
    metadata_db = ProblemMetaDataDB(problem_id=problem.id)
    session.add(metadata_db)
    session.commit()
    session.refresh(metadata_db)

    site_sel = SiteSelectionMetaData(
        metadata_id=metadata_db.id,
        sites_json=json.dumps(SITES),
        nodes_json=json.dumps(NODES),
        travel_time_matrix_json=json.dumps(TRAVEL_TIME_MATRIX),
        site_variable_symbols=SITE_VARS,
        coverage_variable_symbols=COVER_VARS,
        coverage_threshold=15.0,
    )
    session.add(site_sel)
    session.commit()
    session.refresh(site_sel)

    loaded = session.get(SiteSelectionMetaData, site_sel.id)
    assert loaded is not None
    assert loaded.site_variable_symbols == SITE_VARS
    assert loaded.coverage_variable_symbols == COVER_VARS
    assert json.loads(loaded.sites_json) == SITES
    assert json.loads(loaded.nodes_json) == NODES
    assert json.loads(loaded.travel_time_matrix_json) == TRAVEL_TIME_MATRIX
    assert loaded.coverage_threshold == 15.0


def test_site_selection_metadata_coverage_optional(session_and_user: dict):
    """Verify that coverage_variable_symbols=None is accepted."""
    session: Session = session_and_user["session"]

    problem = session.exec(select(ProblemDB)).first()
    metadata_db = ProblemMetaDataDB(problem_id=problem.id)
    session.add(metadata_db)
    session.commit()
    session.refresh(metadata_db)

    site_sel = SiteSelectionMetaData(
        metadata_id=metadata_db.id,
        sites_json=json.dumps(SITES),
        nodes_json=json.dumps(NODES),
        travel_time_matrix_json=json.dumps(TRAVEL_TIME_MATRIX),
        site_variable_symbols=SITE_VARS,
        coverage_variable_symbols=None,
        coverage_threshold=20.0,
    )
    session.add(site_sel)
    session.commit()
    session.refresh(site_sel)

    loaded = session.get(SiteSelectionMetaData, site_sel.id)
    assert loaded is not None
    assert loaded.coverage_variable_symbols is None


# --- Endpoint tests: /site-selection/load_metadata ---


def test_load_metadata_success(client: TestClient, session_and_user: dict):
    """POST with valid data for an owned problem returns 200."""
    access_token = login(client)

    session: Session = session_and_user["session"]
    problem = session.exec(select(ProblemDB)).first()

    payload = {
        "problem_id": problem.id,
        "sites": SITES,
        "nodes": NODES,
        "travel_time_matrix": TRAVEL_TIME_MATRIX,
        "site_variable_symbols": SITE_VARS,
        "coverage_variable_symbols": COVER_VARS,
        "coverage_threshold": 15.0,
    }

    response = post_json(client, "/site-selection/load_metadata", payload, access_token)
    assert response.status_code == 200

    data = response.json()
    assert data["site_variable_symbols"] == SITE_VARS
    assert data["coverage_variable_symbols"] == COVER_VARS

    # Verify in DB
    loaded = session.exec(select(SiteSelectionMetaData)).first()
    assert loaded is not None


def test_load_metadata_wrong_owner(client: TestClient, session_and_user: dict):
    """POST with a problem_id owned by a different user returns 403."""
    session: Session = session_and_user["session"]

    # Create a second user and a problem owned by them
    other_user = User(
        username="other",
        password_hash=get_password_hash("other"),
        role=UserRole.analyst,
        group="test",
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_problem = ProblemDB.from_problem(river_pollution_problem(), user=other_user)
    session.add(other_problem)
    session.commit()
    session.refresh(other_problem)

    # Login as the original "analyst" user
    access_token = login(client)

    payload = {
        "problem_id": other_problem.id,
        "sites": SITES,
        "nodes": NODES,
        "travel_time_matrix": TRAVEL_TIME_MATRIX,
        "site_variable_symbols": SITE_VARS,
    }

    response = post_json(client, "/site-selection/load_metadata", payload, access_token)
    assert response.status_code == 403


def test_load_metadata_problem_not_found(client: TestClient, session_and_user: dict):
    """POST with a nonexistent problem_id returns 404."""
    access_token = login(client)

    payload = {
        "problem_id": 99999,
        "sites": SITES,
        "nodes": NODES,
        "travel_time_matrix": TRAVEL_TIME_MATRIX,
        "site_variable_symbols": SITE_VARS,
    }

    response = post_json(client, "/site-selection/load_metadata", payload, access_token)
    assert response.status_code == 404


# --- Endpoint tests: /site-selection/map ---


def _setup_metadata(session: Session, problem_id: int, coverage: bool = True) -> SiteSelectionMetaData:
    """Helper: create ProblemMetaDataDB + SiteSelectionMetaData for a problem."""
    metadata_db = session.exec(select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == problem_id)).first()
    if metadata_db is None:
        metadata_db = ProblemMetaDataDB(problem_id=problem_id)
        session.add(metadata_db)
        session.commit()
        session.refresh(metadata_db)

    site_sel = SiteSelectionMetaData(
        metadata_id=metadata_db.id,
        sites_json=json.dumps(SITES),
        nodes_json=json.dumps(NODES),
        travel_time_matrix_json=json.dumps(TRAVEL_TIME_MATRIX),
        site_variable_symbols=SITE_VARS,
        coverage_variable_symbols=COVER_VARS if coverage else None,
        coverage_threshold=15.0,
    )
    session.add(site_sel)
    session.commit()
    session.refresh(site_sel)
    return site_sel


def test_map_success(client: TestClient, session_and_user: dict):
    """POST with valid problem_id and solution returns nodes, edges, center."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB)).first()
    _setup_metadata(session, problem.id)

    payload = {
        "problem_id": problem.id,
        "optimal_variables": {"x_1": 1.0, "x_2": 0.0, "x_3": 1.0, "cover_1": 1.0, "cover_2": 0.0},
    }

    response = post_json(client, "/site-selection/map", payload, access_token)
    assert response.status_code == 200

    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "center" in data
    assert len(data["nodes"]) == 2
    assert len(data["center"]) == 2


def test_map_no_metadata(client: TestClient, session_and_user: dict):
    """POST with a problem_id that has no SiteSelectionMetaData returns 404."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    # Use a problem that has no site selection metadata (river pollution from conftest)
    problem = session.exec(select(ProblemDB).where(ProblemDB.name == "The river pollution problem")).first()

    payload = {
        "problem_id": problem.id,
        "optimal_variables": {},
    }

    response = post_json(client, "/site-selection/map", payload, access_token)
    # Could be 404 — river pollution has ProblemMetaDataDB from conftest but no site_selection_metadata
    assert response.status_code == 404


def test_map_color_active(client: TestClient, session_and_user: dict):
    """A node hosting a visited site receives COLOR_ACTIVE (#FFA500)."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB)).first()
    _setup_metadata(session, problem.id)

    # x_1 and x_2 are in CityA, x_3 is in CityB — visit only x_1
    payload = {
        "problem_id": problem.id,
        "optimal_variables": {"x_1": 1.0, "x_2": 0.0, "x_3": 0.0, "cover_1": 0.0, "cover_2": 0.0},
    }

    response = post_json(client, "/site-selection/map", payload, access_token)
    assert response.status_code == 200

    data = response.json()
    city_a = next(n for n in data["nodes"] if n["name"] == "CityA")
    assert city_a["color"] == "#FFA500"


def test_map_color_inactive(client: TestClient, session_and_user: dict):
    """A node with no visited sites and no coverage receives COLOR_INACTIVE (#808080)."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB)).first()
    _setup_metadata(session, problem.id)

    # Visit x_1 (CityA only), no coverage
    payload = {
        "problem_id": problem.id,
        "optimal_variables": {"x_1": 1.0, "x_2": 0.0, "x_3": 0.0, "cover_1": 0.0, "cover_2": 0.0},
    }

    response = post_json(client, "/site-selection/map", payload, access_token)
    assert response.status_code == 200

    data = response.json()
    city_b = next(n for n in data["nodes"] if n["name"] == "CityB")
    assert city_b["color"] == "#808080"


def test_map_no_coverage_variables(client: TestClient, session_and_user: dict):
    """POST with metadata where coverage_variable_symbols=None returns 200 with no edges."""
    session: Session = session_and_user["session"]
    access_token = login(client)

    problem = session.exec(select(ProblemDB)).first()
    _setup_metadata(session, problem.id, coverage=False)

    payload = {
        "problem_id": problem.id,
        "optimal_variables": {"x_1": 1.0, "x_2": 0.0, "x_3": 0.0},
    }

    response = post_json(client, "/site-selection/map", payload, access_token)
    assert response.status_code == 200

    data = response.json()
    assert data["edges"] == []
