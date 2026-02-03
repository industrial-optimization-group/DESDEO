from fastapi.testclient import TestClient  # noqa: D100
from sqlmodel import select

from desdeo.api.models import ProblemDB, ProblemMetaDataDB, RepresentativeNonDominatedSolutions
from desdeo.problem.testproblems import dtlz2

from .conftest import login


def test_add_representative_solution_set(client: TestClient, session_and_user: dict):
    """Test that the representative solution set can be added via the endpoint."""
    session = session_and_user["session"]
    user = session_and_user["user"]

    # --- login to get access token ---
    access_token = login(client)

    # --- create a test problem ---
    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)

    # --- prepare solution set JSON ---
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
        json=solution_set_payload,  # <--- send JSON body
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Representative solution set added successfully."

    # --- verify DB ---
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
