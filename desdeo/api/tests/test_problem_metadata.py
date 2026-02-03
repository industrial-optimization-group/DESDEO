from fastapi.testclient import TestClient  # noqa: D100
from sqlmodel import select

from desdeo.api.models import ProblemDB, ProblemMetaDataDB, RepresentativeNonDominatedSolutions
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

    # Prepare solution set JSON
    solution_set_payload = {
        "problem_id": problem.id,
        "name": "Test solutions",
        "description": "Solutions for testing",
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

    response = client.post(
        "/problem/add_representative_solution_set",
        headers={"Authorization": f"Bearer {access_token}"},
        json=solution_set_payload,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Representative solution set added successfully."

    # Verify DB
    statement = select(ProblemMetaDataDB).where(ProblemMetaDataDB.problem_id == problem.id)
    metadata = session.exec(statement).first()
    assert metadata is not None
    assert metadata.problem_id == problem.id

    repr_metadata = metadata.representative_nd_metadata[0]
    assert isinstance(repr_metadata, RepresentativeNonDominatedSolutions)
    assert repr_metadata.name == solution_set_payload["name"]
    assert repr_metadata.description == solution_set_payload["description"]
    assert repr_metadata.solution_data == solution_set_payload["solution_data"]
    assert repr_metadata.ideal == solution_set_payload["ideal"]
    assert repr_metadata.nadir == solution_set_payload["nadir"]

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

    # Add a representative solution set
    solution_set = RepresentativeNonDominatedSolutions(
        metadata_id=None,
        name="Test Set GET",
        description="Description GET",
        solution_data={"x": [1.0, 2.0], "f": [0.1, 0.2]},
        ideal={"f_1": 0.1},
        nadir={"f_1": 0.2},
        metadata_instance=None
    )

    # Attach problem metadata
    problem_metadata = ProblemMetaDataDB(problem_id=problem.id, problem=problem)
    session.add(problem_metadata)
    session.commit()
    session.refresh(problem_metadata)

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
        f"/problem/all_representative_solution_sets/{problem.id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200

    data = response.json()
    assert data["problem_id"] == problem.id
    assert len(data["representative_sets"]) == 1

    repr_meta = data["representative_sets"][0]
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
        "problem_id": problem.id,
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
        "/problem/add_representative_solution_set",
        headers={"Authorization": f"Bearer {access_token}"},
        json=solution_set_payload,
    )
    assert post_response.status_code == 200

    # Fetch the added representative set from DB
    repr_metadata = session.exec(
        select(RepresentativeNonDominatedSolutions)
        .where(RepresentativeNonDominatedSolutions.name == "Full Test Solution Set")
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

    # Add a representative solution set
    repr_metadata = RepresentativeNonDominatedSolutions(
        metadata_id=ProblemMetaDataDB(problem_id=problem.id, problem=problem).id,
        metadata_instance=ProblemMetaDataDB(problem_id=problem.id, problem=problem),
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
    assert response.status_code == 200
    assert response.json()["detail"] == "Deleted successfully"

    # Verify DB deletion
    deleted_set = session.get(RepresentativeNonDominatedSolutions, repr_metadata.id)
    assert deleted_set is None
