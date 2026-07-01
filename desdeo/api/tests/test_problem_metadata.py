"""Tests for problem metadata API endpoints.

Covers representative solution sets and solution description metadata.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlmodel import select

from desdeo.api.models import ProblemDB, ProblemMetaDataDB, RepresentativeNonDominatedSolutions
from desdeo.api.models.problem import SolutionDescriptionMetaData
from desdeo.api.models.representative_solution import RepresentativeSolutionSetBase
from desdeo.api.routers.utils import SessionContextGuard
from desdeo.problem.testproblems import dtlz2

from .conftest import login


def test_add_representative_solution_set(client: TestClient, session_and_user: dict):
    """Test that the representative solution set can be added via the endpoint."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    access_token = login(client)

    # Create a test problem
    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    def test_guard(user, db_session, request=None, problem_id=None):
        # problem_id comes from the URL
        return SimpleNamespace(
            user=user,
            db_session=db_session,
            problem_db=problem,
            interactive_session=None,
            parent_state=None,
        )

    client.app.dependency_overrides[SessionContextGuard] = test_guard

    solution_set_model = RepresentativeSolutionSetBase(
        name="Test solutions",
        description="Solutions for testing",
        solution_data={
            "x_1": [1.1, 2.2, 3.3],
            "x_2": [-1.1, -2.2, -3.3],
            "f_1": [0.1, 0.5, 0.9],
            "f_2": [-0.1, 0.2, 199.2],
            "f_1_min": [],
            "f_2_min": [],
        },
        ideal={"f_1": 0.1, "f_2": -0.1},
        nadir={"f_1": 0.9, "f_2": 199.2},
    )

    response = client.post(
        f"/problem/{problem.id}/add_representative_solution_set",
        headers={"Authorization": f"Bearer {access_token}"},
        json=solution_set_model.model_dump(),  # send as JSON
    )

    # Clean up override
    client.app.dependency_overrides = {}

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == solution_set_model.name
    assert data["description"] == solution_set_model.description
    assert data["ideal"] == solution_set_model.ideal
    assert data["nadir"] == solution_set_model.nadir

    # Verify DB
    statement = select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == problem.id)
    metadata = session.exec(statement).first()
    assert metadata is not None
    assert metadata.problem_id == problem.id

    repr_metadata = metadata.representative_nd_metadata[0]
    assert isinstance(repr_metadata, RepresentativeNonDominatedSolutions)
    assert repr_metadata.name == solution_set_model.name
    assert repr_metadata.description == solution_set_model.description
    assert repr_metadata.solution_data == solution_set_model.solution_data
    assert repr_metadata.ideal == solution_set_model.ideal
    assert repr_metadata.nadir == solution_set_model.nadir


def test_get_all_representative_solution_sets(client: TestClient, session_and_user: dict):
    """Test that all representative solution sets for a problem can be fetched (meta-level)."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    access_token = login(client)

    # Create a test problem
    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    # Attach problem metadata
    problem_metadata = ProblemMetaDataDB(problem_id=problem.id, problem=problem)
    session.add(problem_metadata)
    session.commit()
    session.refresh(problem_metadata)

    # Add a representative solution set
    solution_set = RepresentativeNonDominatedSolutions(
        metadata_id=None,
        metadata_instance=None,
        name="Test Set GET",
        description="Description GET",
        solution_data={"x": [1.0, 2.0], "f": [0.1, 0.2]},
        ideal={"f_1": 0.1},
        nadir={"f_1": 0.2},
    )

    # Attach the representative set
    solution_set.metadata_id = problem_metadata.id
    solution_set.metadata_instance = problem_metadata
    session.add(solution_set)
    problem_metadata.representative_nd_metadata.append(solution_set)
    session.add_all([solution_set, problem_metadata])
    session.commit()
    session.refresh(problem_metadata)

    # Call GET endpoint
    response = client.get(
        f"/problem/{problem.id}/all_representative_solution_sets", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    repr_meta = data[0]
    assert repr_meta["name"] == "Test Set GET"
    assert repr_meta["description"] == "Description GET"
    assert repr_meta["ideal"] == {"f_1": 0.1}
    assert repr_meta["nadir"] == {"f_1": 0.2}


def test_get_representative_solution_set(client: TestClient, session_and_user: dict):
    """Test that a single representative solution set can be fetched by its ID."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    access_token = login(client)

    # Create a test problem
    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    # Add a representative solution set
    solution_set_payload = {
        "name": "Full Test Solution Set",
        "description": "Full info for testing",
        "solution_data": {
            "x_1": [1.1, 2.2, 3.3],
            "x_2": [-1.1, -2.2, -3.3],
            "f_1": [0.1, 0.5, 0.9],
            "f_2": [-0.1, 0.2, 199.2],
            "f_1_min": [],
            "f_2_min": [],
        },
        "ideal": {"f_1": 0.1, "f_2": -0.1},
        "nadir": {"f_1": 0.9, "f_2": 199.2},
    }

    post_response = client.post(
        f"/problem/{problem.id}/add_representative_solution_set",
        headers={"Authorization": f"Bearer {access_token}"},
        json=solution_set_payload,
    )
    assert post_response.status_code == 200

    # Fetch the added representative set from DB
    repr_metadata = session.exec(
        select(RepresentativeNonDominatedSolutions).where(
            RepresentativeNonDominatedSolutions.name == "Full Test Solution Set"
        )
    ).first()
    assert repr_metadata is not None

    # Call the GET endpoint
    get_response = client.get(
        f"/problem/representative_solution_set/{repr_metadata.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert get_response.status_code == 200

    # Verify returned data
    data = get_response.json()
    assert data["id"] == repr_metadata.id
    assert data["name"] == solution_set_payload["name"]
    assert data["description"] == solution_set_payload["description"]
    assert data["solution_data"] == solution_set_payload["solution_data"]
    assert data["ideal"] == solution_set_payload["ideal"]
    assert data["nadir"] == solution_set_payload["nadir"]


def test_delete_representative_solution_set(client: TestClient, session_and_user: dict):
    """Test that a representative solution set can be deleted by its ID."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    access_token = login(client)

    # Create test problem
    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    # Create metadata properly
    problem_metadata = ProblemMetaDataDB(problem_id=problem.id, problem=problem)
    session.add(problem_metadata)
    session.commit()
    session.refresh(problem_metadata)

    # Add a representative solution set
    repr_metadata = RepresentativeNonDominatedSolutions(
        metadata_id=problem_metadata.id,
        metadata_instance=problem_metadata,
        name="To be deleted",
        description="Test deletion",
        solution_data={"x": [1.0], "f": [0.0]},
        ideal={"f": 0.0},
        nadir={"f": 1.0},
    )
    session.add(repr_metadata)
    session.commit()
    session.refresh(repr_metadata)

    # Call DELETE request
    response = client.delete(
        f"/problem/representative_solution_set/{repr_metadata.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 204
    assert response.content == b""

    # Verify DB deletion
    deleted_set = session.get(RepresentativeNonDominatedSolutions, repr_metadata.id)
    assert deleted_set is None


def test_update_solution_description_metadata(client: TestClient, session_and_user: dict):
    """Test that solution description metadata can be added via the update endpoint."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    access_token = login(client)

    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    problem_metadata = ProblemMetaDataDB(problem_id=problem.id, problem=problem)
    session.add(problem_metadata)
    session.commit()
    session.refresh(problem_metadata)

    payload = {
        "problem_id": problem.id,
        "separator": " | ",
        "parts": [
            {"text": "Solution quality"},
            {"symbol": "f_1", "label": "Objective 1", "format_spec": ".2f", "suffix": "%"},
        ],
    }

    response = client.post(
        "/solution-description/update_metadata",
        headers={"Authorization": f"Bearer {access_token}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["separator"] == " | "
    assert len(data["parts"]) == 2
    assert data["parts"][0]["text"] == "Solution quality"
    assert data["parts"][1]["symbol"] == "f_1"

    # Verify the row is in the DB and linked to the metadata record
    db_entry = session.get(SolutionDescriptionMetaData, data["id"])
    assert db_entry is not None
    assert db_entry.metadata_id == problem_metadata.id
    assert db_entry.separator == " | "


def test_update_solution_description_metadata_appends(client: TestClient, session_and_user: dict):
    """Test that calling update twice appends a second entry, and the latest is used."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    access_token = login(client)

    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    problem_metadata = ProblemMetaDataDB(problem_id=problem.id, problem=problem)
    session.add(problem_metadata)
    session.commit()
    session.refresh(problem_metadata)

    for sep in ["\n", " -- "]:
        response = client.post(
            "/solution-description/update_metadata",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"problem_id": problem.id, "separator": sep, "parts": [{"text": "hello"}]},
        )
        assert response.status_code == 200

    session.refresh(problem_metadata)
    assert len(problem_metadata.solution_description_metadata) == 2
    assert problem_metadata.solution_description_metadata[-1].separator == " -- "


def test_update_solution_description_metadata_invalid_expression(client: TestClient, session_and_user: dict):
    """Test that an unparseable expression is rejected with 422."""
    session = session_and_user["session"]
    user = session_and_user["user"]
    access_token = login(client)

    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    problem_metadata = ProblemMetaDataDB(problem_id=problem.id, problem=problem)
    session.add(problem_metadata)
    session.commit()

    response = client.post(
        "/solution-description/update_metadata",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "problem_id": problem.id,
            "separator": "\n",
            "parts": [{"expression": "this is not valid mathjson"}],
        },
    )

    assert response.status_code == 422


def test_update_solution_description_metadata_missing_problem(client: TestClient, session_and_user: dict):
    """Test that updating metadata for a non-existent problem metadata record returns 404."""
    access_token = login(client)

    response = client.post(
        "/solution-description/update_metadata",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"problem_id": 99999, "separator": "\n", "parts": [{"text": "hi"}]},
    )

    assert response.status_code == 404
