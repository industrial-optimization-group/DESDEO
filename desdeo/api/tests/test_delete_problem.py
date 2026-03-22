"""Tests for the DELETE /problem/{problem_id} endpoint."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from desdeo.api.models import ProblemDB, ProblemMetaDataDB, RepresentativeNonDominatedSolutions, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dtlz2, river_pollution_problem

from .conftest import login


def test_delete_problem_success(client: TestClient, session_and_user: dict):
    """Test that a problem can be deleted by its owner."""
    session: Session = session_and_user["session"]
    user: User = session_and_user["user"]
    access_token = login(client)

    # Create a fresh problem for deletion
    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)
    problem_id = problem.id

    response = client.delete(
        f"/problem/{problem_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""

    # Verify the problem is gone
    deleted = session.get(ProblemDB, problem_id)
    assert deleted is None


def test_delete_problem_cascades_children(client: TestClient, session_and_user: dict):
    """Test that deleting a problem also removes its metadata and child records."""
    session: Session = session_and_user["session"]
    user: User = session_and_user["user"]
    access_token = login(client)

    # Create problem with metadata and representative solutions
    problem = ProblemDB.from_problem(river_pollution_problem(), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)
    problem_id = problem.id

    metadata = ProblemMetaDataDB(problem_id=problem.id, problem=problem)
    session.add(metadata)
    session.commit()
    session.refresh(metadata)
    metadata_id = metadata.id

    repr_set = RepresentativeNonDominatedSolutions(
        metadata_id=metadata.id,
        metadata_instance=metadata,
        name="Test set",
        description="Will be cascade-deleted",
        solution_data={"x": [1.0], "f": [0.0]},
        ideal={"f": 0.0},
        nadir={"f": 1.0},
    )
    session.add(repr_set)
    session.commit()
    session.refresh(repr_set)
    repr_set_id = repr_set.id

    response = client.delete(
        f"/problem/{problem_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # All children should be gone
    assert session.get(ProblemDB, problem_id) is None
    assert session.get(ProblemMetaDataDB, metadata_id) is None
    assert session.get(RepresentativeNonDominatedSolutions, repr_set_id) is None


def test_delete_problem_not_found(client: TestClient, session_and_user: dict):
    """Test that deleting a non-existent problem returns 404."""
    access_token = login(client)

    response = client.delete(
        "/problem/99999",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_problem_unauthorized(client: TestClient, session_and_user: dict):
    """Test that a user cannot delete another user's problem."""
    session: Session = session_and_user["session"]
    user: User = session_and_user["user"]

    # Create a second user
    other_user = User(
        username="other",
        password_hash=get_password_hash("other"),
        role=UserRole.analyst,
        group="test",
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    # Create a problem owned by the original user
    problem = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem)
    session.commit()
    session.refresh(problem)
    problem_id = problem.id

    # Login as the other user and try to delete
    other_token = login(client, username="other", password="other")

    response = client.delete(
        f"/problem/{problem_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Problem should still exist
    assert session.get(ProblemDB, problem_id) is not None


def test_delete_problem_unauthenticated(client: TestClient, session_and_user: dict):
    """Test that deleting without auth returns 401."""
    response = client.delete("/problem/1")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_delete_problem_does_not_affect_others(client: TestClient, session_and_user: dict):
    """Test that deleting one problem does not affect other problems."""
    session: Session = session_and_user["session"]
    user: User = session_and_user["user"]
    access_token = login(client)

    # Create two problems
    problem_a = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    problem_b = ProblemDB.from_problem(dtlz2(5, 3), user=user)
    session.add(problem_a)
    session.add(problem_b)
    session.commit()
    session.refresh(problem_a)
    session.refresh(problem_b)

    # Delete only problem_a
    response = client.delete(
        f"/problem/{problem_a.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(ProblemDB, problem_a.id) is None
    assert session.get(ProblemDB, problem_b.id) is not None
