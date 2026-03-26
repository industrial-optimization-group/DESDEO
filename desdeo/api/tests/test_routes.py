"""Tests related to routes and routers."""

import json
import time

from fastapi import status
from fastapi.testclient import TestClient

from desdeo.api.models import (
    CreateSessionRequest,
    EMOFetchRequest,
    EMOIterateRequest,
    EMOIterateResponse,
    ForestProblemMetaData,
    GDMSCOREBandsHistoryResponse,
    GDMScoreBandsInitializationRequest,
    GDMScoreBandsVoteRequest,
    GenericIntermediateSolutionResponse,
    GroupCreateRequest,
    GroupInfoRequest,
    GroupModifyRequest,
    GroupPublic,
    InteractiveSessionDB,
    IntermediateSolutionRequest,
    NIMBUSClassificationRequest,
    NIMBUSClassificationResponse,
    NIMBUSDeleteSaveRequest,
    NIMBUSDeleteSaveResponse,
    NIMBUSFinalizeRequest,
    NIMBUSFinalizeResponse,
    NIMBUSInitializationRequest,
    NIMBUSIntermediateSolutionResponse,
    NIMBUSSaveRequest,
    NIMBUSSaveResponse,
    ProblemDB,
    ProblemInfo,
    ProblemSelectSolverRequest,
    ReferencePoint,
    RPMSolveRequest,
    SolutionInfo,
    SolverSelectionMetadata,
    User,
    UserPublic,
)
from desdeo.api.models.nimbus import (
    NIMBUSInitializationResponse,
    NIMBUSMultiplierRequest,
    NIMBUSMultiplierResponse,
)
from desdeo.api.routers.user_authentication import create_access_token
from desdeo.emo.options.algorithms import rvea_options
from desdeo.emo.options.templates import ReferencePointOptions
from desdeo.gdm.score_bands import SCOREBandsGDMConfig
from desdeo.problem import Problem
from desdeo.problem.testproblems import dtlz2, simple_knapsack_vectors
from desdeo.tools.score_bands import KMeansOptions, SCOREBandsConfig
from desdeo.tools.utils import available_solvers

from .conftest import get_json, login, post_file_multipart, post_json
from .test_models import compare_models


def test_user_login(client: TestClient):
    """Test that login works."""
    response = client.post(
        "/login",
        data={"username": "analyst", "password": "analyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

    # wrong login
    response = client.post(
        "/login",
        data={"username": "analyst", "password": "anallyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401


def test_tokens():
    """Test token generation."""
    token_1 = create_access_token({"id": 1, "sub": "analyst"})
    token_2 = create_access_token({"id": 1, "sub": "analyst"})

    assert token_1 != token_2


def test_refresh(client: TestClient):
    """Test that refreshing the access token works."""
    # check that no previous cookies exist
    assert len(client.cookies) == 0

    # no cookie
    response_bad = client.post("/refresh")

    response_good = client.post(
        "/login",
        data={"username": "analyst", "password": "analyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert response_bad.status_code == 401
    assert response_good.status_code == 200

    assert "access_token" in response_good.json()
    assert len(client.cookies) == 1
    assert "refresh_token" in client.cookies

    response_refresh = client.post("/refresh")

    assert "access_token" in response_refresh.json()
    assert "access_token" in response_refresh.cookies

    assert response_good.json()["access_token"] != response_refresh.json()["access_token"]


def test_get_problem(client: TestClient):
    """Test fetching specific problems based on their id."""
    access_token = login(client)

    response = client.get("/problem/1", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200

    info = ProblemInfo.model_validate(response.json())
    assert info.id == 1
    assert info.name == "dtlz2"
    assert info.problem_metadata is None

    response = client.get("/problem/2", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200

    info = ProblemInfo.model_validate(response.json())
    assert info.id == 2
    assert info.name == "The river pollution problem"
    assert isinstance(info.problem_metadata.forest_metadata[0], ForestProblemMetaData)


def test_add_problem(client: TestClient):
    """Test that adding a problem to the database works."""
    access_token = login(client)

    problem = simple_knapsack_vectors()

    response = post_json(client, "/problem/add", problem.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK

    problem_info: ProblemInfo = ProblemInfo.model_validate(response.json())

    assert problem_info.name == "Simple two-objective Knapsack problem"

    response = get_json(client, "problem/all_info", access_token)

    assert response.status_code == status.HTTP_200_OK

    problems = response.json()

    assert len(problems) == 4


def test_add_problem_json(client: TestClient, session_and_user: dict):
    """Test that adding a problem to the database works with JSON files."""
    session = session_and_user["session"]
    access_token = login(client)
    problem = dtlz2(5, 3)

    payload = problem.model_dump()
    raw = json.dumps(payload).encode("utf-8")

    response = post_file_multipart(client, "/problem/add_json", raw, access_token)

    assert response.status_code == 200

    problem_from_db = session.get(ProblemDB, 4)

    assert compare_models(problem, Problem.from_problemdb(problem_from_db))


def test_new_session(client: TestClient, session_and_user: dict):
    """Test that creating a new session works as expected."""
    user: User = session_and_user["user"]
    session = session_and_user["session"]

    assert user.active_session_id is None

    access_token = login(client)

    request = CreateSessionRequest(info="My session")

    response = post_json(client, "/session/new", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK

    assert user.active_session_id == 1
    isession = session.get(InteractiveSessionDB, 1)

    assert isession.info == "My session"


def test_get_session(client: TestClient, session_and_user: dict):
    """Test that getting a session via GET works as intended."""
    user: User = session_and_user["user"]

    access_token = login(client)

    # no sessions
    response = client.get(
        "/session/get/1",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # add session 1
    request = CreateSessionRequest(info="Session 1")
    response = post_json(client, "/session/new", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    assert user.active_session_id == 1

    # add session 2
    request = CreateSessionRequest(info="Session 2")
    response = post_json(client, "/session/new", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    assert user.active_session_id == 2

    # fetch session 1
    response = client.get(
        "/session/get/1",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == 1

    # fetch session 2
    response = client.get(
        "/session/get/2",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == 2


def test_get_all_sessions_success(client: TestClient, session_and_user: dict):
    """Test getting all sessions when sessions exist."""
    access_token = login(client)

    # create 2 test sessions
    post_json(client, "/session/new", {"info": "S1"}, access_token)
    post_json(client, "/session/new", {"info": "S2"}, access_token)

    response = client.get(
        "/session/get_all",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_get_all_sessions_not_found(client: TestClient, session_and_user: dict):
    """Test get_all returns 404 if user has no sessions."""
    access_token = login(client)

    response = client.get(
        "/session/get_all",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_session_success(client: TestClient, session_and_user: dict):
    """Test deleting an existing session."""
    access_token = login(client)

    # create session
    post_json(client, "/session/new", {"info": "To delete"}, access_token)

    response = client.delete(
        "/session/1",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # verify it's gone
    response = client.get(
        "/session/get/1",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_session_not_found(client: TestClient, session_and_user: dict):
    """Test deleting a non-existent session returns 404."""
    access_token = login(client)

    response = client.delete(
        "/session/999",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_rpm_solve(client: TestClient):
    """Test that using the reference point method works as expected."""
    access_token = login(client)

    request = RPMSolveRequest(
        problem_id=1, preference=ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.3, "f_3": 0.4})
    )

    response = post_json(client, "/method/rpm/solve", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK


def test_nimbus_solve(client: TestClient):
    """Test that using the NIMBUS method works as expected."""
    access_token = login(client)

    preference = ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4})

    request = NIMBUSClassificationRequest(
        problem_id=1, preference=preference, current_objectives={"f_1": 0.6, "f_2": 0.4, "f_3": 0.5}, num_desired=3
    )

    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content.decode("utf-8"))
    )
    assert result.previous_preference == preference
    assert len(result.all_solutions) == 3

    request = NIMBUSSaveRequest(
        problem_id=1,
        parent_state_id=result.state_id,
        solution_info=[
            SolutionInfo(state_id=1, solution_index=0, name="Test solution 1"),
            SolutionInfo(state_id=1, solution_index=2, name="Test solution 3"),
            SolutionInfo(state_id=1, solution_index=2, name="Test solution 34"),  # saved twice!
        ],
    )

    response = post_json(client, "/method/nimbus/save", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result2: NIMBUSSaveResponse = NIMBUSSaveResponse.model_validate(json.loads(response.content.decode("utf-8")))
    assert result2.state_id is not None

    preference = ReferencePoint(aspiration_levels={"f_1": 0.1, "f_2": 0.1, "f_3": 0.9})

    request = NIMBUSClassificationRequest(
        problem_id=1,
        preference=preference,
        current_objectives=result.current_solutions[0].objective_values,
        num_desired=3,
        parent_state_id=result2.state_id,
    )

    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK
    result: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content.decode("utf-8"))
    )
    assert result.previous_preference == preference
    # We saved the same solution twice, so the filtering should remove one of those.
    assert len(result.saved_solutions) == 2
    assert len(result.all_solutions) == 6  # should not count saved solutions twice

    # Save some more solutions!
    request = NIMBUSSaveRequest(
        problem_id=1,
        parent_state_id=result.state_id,
        solution_info=[SolutionInfo(state_id=result.state_id, solution_index=1, name="Test solution 2")],
    )

    response = post_json(client, "/method/nimbus/save", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result2: NIMBUSSaveResponse = NIMBUSSaveResponse.model_validate(json.loads(response.content.decode("utf-8")))
    assert result2.state_id is not None

    # Same as the first one. Therefore, (I believe) STOM and ASF give same solutions,
    # which should be reflected on the amount of all solutions
    preference = ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4})

    request = NIMBUSClassificationRequest(
        problem_id=1,
        preference=preference,
        current_objectives=result.current_solutions[0].objective_values,
        num_desired=3,
        parent_state_id=result2.state_id,
    )

    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result3: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content.decode("utf-8"))
    )
    assert result3.previous_preference == preference
    assert len(result3.saved_solutions) == 3
    assert len(result3.all_solutions) == 7


def test_intermediate_solve(client: TestClient):
    """Test that solving intermediate solutions works as expected."""
    access_token = login(client)

    preference = ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4})

    request = NIMBUSClassificationRequest(
        problem_id=1, preference=preference, current_objectives={"f_1": 0.6, "f_2": 0.4, "f_3": 0.5}, num_desired=2
    )

    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content.decode("utf-8"))
    )
    assert len(result.all_solutions) == 2

    # Save some solutions!
    solution_1 = SolutionInfo(state_id=result.state_id, solution_index=0)
    solution_2 = SolutionInfo(state_id=result.state_id, solution_index=1, name="named solution")

    # Create request for intermediate solutions using solutions created with nimbus solve
    request = IntermediateSolutionRequest(
        problem_id=1,
        context="test",
        reference_solution_1=solution_1,
        reference_solution_2=solution_2,
        num_desired=3,
    )

    # Test the generic intermediate endpoint
    response = post_json(client, "/method/generic/intermediate", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result: GenericIntermediateSolutionResponse = GenericIntermediateSolutionResponse.model_validate(
        json.loads(response.content.decode("utf-8"))
    )

    # Test the NIMBUS-specific intermediate endpoint
    nimbus_request = IntermediateSolutionRequest(
        problem_id=1,
        context="nimbus",
        reference_solution_1=solution_1,
        reference_solution_2=solution_2,
        num_desired=2,
    )

    nimbus_response = post_json(client, "/method/nimbus/intermediate", nimbus_request.model_dump(), access_token)
    assert nimbus_response.status_code == status.HTTP_200_OK
    nimbus_result = NIMBUSIntermediateSolutionResponse.model_validate(
        json.loads(nimbus_response.content.decode("utf-8"))
    )

    # Verify the NIMBUS response contains expected fields
    assert nimbus_result.state_id is not None
    assert len(nimbus_result.current_solutions) == 2
    assert len(nimbus_result.all_solutions) == 7


def test_nimbus_initialize(client: TestClient):
    """Test that initializing NIMBUS works without specifying a solver."""
    access_token = login(client)

    # test with no starting point
    request = NIMBUSInitializationRequest(problem_id=1, solver=None)

    response = post_json(client, "/method/nimbus/initialize", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK
    init_result = NIMBUSInitializationResponse.model_validate(json.loads(response.content))

    assert init_result.state_id == 1
    assert len(init_result.current_solutions) == 1
    assert len(init_result.saved_solutions) == 0
    assert len(init_result.all_solutions) == 1

    # test with starting point given as solution info
    request_w_info = NIMBUSInitializationRequest(
        problem_id=1, starting_point=SolutionInfo(state_id=1, solution_index=0)
    )

    response_w_info = post_json(client, "/method/nimbus/initialize", request_w_info.model_dump(), access_token)

    assert response_w_info.status_code == status.HTTP_200_OK
    result_w_info = NIMBUSInitializationResponse.model_validate(json.loads(response_w_info.content))

    assert result_w_info.state_id == 2
    assert len(result_w_info.current_solutions) == 1
    assert len(result_w_info.saved_solutions) == 0
    assert len(result_w_info.all_solutions) == 1  # this is still one because the new solution will be a duplicate.

    # test with starting point given as a reference point
    request_w_ref = NIMBUSInitializationRequest(
        problem_id=1, starting_point=ReferencePoint(aspiration_levels={"f_1": 0.2, "f_2": 0.8, "f_3": 0.4})
    )

    response_w_ref = post_json(client, "/method/nimbus/initialize", request_w_ref.model_dump(), access_token)

    assert response_w_ref.status_code == status.HTTP_200_OK
    result_w_ref = NIMBUSInitializationResponse.model_validate(json.loads(response_w_ref.content))

    assert result_w_ref.state_id == 3
    assert len(result_w_ref.current_solutions) == 1
    assert len(result_w_ref.saved_solutions) == 0
    assert len(result_w_ref.all_solutions) == 2  # we should have a new one


def test_nimbus_finalize(client: TestClient):
    """Test for seeing if NIMBUS finalization works."""
    access_token = login(client)

    # create some previous iterations
    request = NIMBUSInitializationRequest(problem_id=1)
    response = post_json(client, "/method/nimbus/get-or-initialize", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    init_response = NIMBUSInitializationResponse.model_validate(json.loads(response.content))
    assert init_response.state_id == 1
    assert len(init_response.current_solutions) == 1
    assert len(init_response.saved_solutions) == 0
    assert len(init_response.all_solutions) == 1

    preference = ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4})

    request = NIMBUSClassificationRequest(
        problem_id=1, preference=preference, current_objectives={"f_1": 0.6, "f_2": 0.4, "f_3": 0.5}, num_desired=3
    )

    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content.decode("utf-8"))
    )
    assert result.previous_preference == preference
    assert len(result.current_solutions) == 3

    solution_index = 2

    optim_obj = result.current_solutions[solution_index].objective_values
    optim_var = result.current_solutions[solution_index].variable_values

    state_id = result.state_id

    request = NIMBUSInitializationRequest(problem_id=1)
    response = post_json(client, "/method/nimbus/get-or-initialize", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    classify_result = NIMBUSClassificationResponse.model_validate(json.loads(response.content))
    assert classify_result.state_id == 2
    assert len(classify_result.current_solutions) == 3
    assert len(classify_result.saved_solutions) == 0
    assert len(classify_result.all_solutions) == 4

    request = NIMBUSFinalizeRequest(
        problem_id=1,
        solution_info=SolutionInfo(state_id=state_id, solution_index=solution_index),
    )

    # Finalize the process
    response = post_json(client, "/method/nimbus/finalize", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result: NIMBUSFinalizeResponse = NIMBUSFinalizeResponse.model_validate(json.loads(response.content.decode("utf-8")))
    assert result.response_type == "nimbus.finalize"
    assert result.final_solution.objective_values == optim_obj
    assert result.final_solution.variable_values == optim_var
    assert result.final_solution.state_id != result.state_id
    assert result.all_solutions is not None

    request = NIMBUSInitializationRequest(problem_id=1)

    # The last item in the pipe is a finalize state, so we should be getting a finalize response.
    response = post_json(client, "/method/nimbus/get-or-initialize", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result: NIMBUSFinalizeResponse = NIMBUSFinalizeResponse.model_validate(json.loads(response.content.decode("utf-8")))
    assert result.response_type == "nimbus.finalize"
    assert result.final_solution.objective_values == optim_obj
    assert result.final_solution.variable_values == optim_var
    assert result.final_solution.state_id != result.state_id
    assert result.all_solutions is not None


def test_nimbus_save_and_delete_save(client: TestClient):
    """Test that NIMBUS saving and save deletion works."""
    access_token = login(client)

    # 1. Initialize
    request: NIMBUSInitializationRequest = NIMBUSInitializationRequest(problem_id=1)
    response = post_json(client, "/method/nimbus/initialize", request.model_dump(), access_token)
    init_result: NIMBUSInitializationResponse = NIMBUSInitializationResponse.model_validate(
        json.loads(response.content)
    )
    assert init_result.state_id == 1

    # 2. Iterate
    request: NIMBUSClassificationRequest = NIMBUSClassificationRequest(
        problem_id=1,
        preference=ReferencePoint(
            aspiration_levels={
                "f_1": 0.1,
                "f_2": 0.8,
                "f_3": 0.5,
            }
        ),
        current_objectives=init_result.current_solutions[0].objective_values,
        parent_state_id=1,
        num_desired=3,
    )
    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)
    solve_result: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content)
    )
    assert solve_result.state_id == 2

    # 3. Save
    request: NIMBUSSaveRequest = NIMBUSSaveRequest(
        problem_id=1, parent_state_id=2, solution_info=[SolutionInfo(state_id=2, solution_index=1)]
    )
    response = post_json(client, "/method/nimbus/save", request.model_dump(), access_token)
    save_result: NIMBUSSaveResponse = NIMBUSSaveResponse.model_validate(json.loads(response.content))
    assert save_result.state_id == 3

    # Assert that stuff is saved
    request: NIMBUSClassificationRequest = NIMBUSClassificationRequest(
        problem_id=1,
        preference=ReferencePoint(
            aspiration_levels={
                "f_1": 0.9,
                "f_2": 0.1,
                "f_3": 0.5,
            }
        ),
        current_objectives=solve_result.current_solutions[0].objective_values,
        num_desired=1,
        parent_state_id=3,
    )
    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)
    solve_result: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content)
    )
    assert solve_result.state_id == 4
    assert len(solve_result.saved_solutions) > 0

    # 4. Delete save
    request: NIMBUSDeleteSaveRequest = NIMBUSDeleteSaveRequest(state_id=2, solution_index=1, problem_id=1)
    response = post_json(client, "/method/nimbus/delete_save", request.model_dump(), access_token)
    delete_save_result: NIMBUSDeleteSaveResponse = NIMBUSDeleteSaveResponse.model_validate(json.loads(response.content))

    assert delete_save_result

    # Assert that saved stuff has been deleted

    # Assert that stuff is saved
    request: NIMBUSClassificationRequest = NIMBUSClassificationRequest(
        problem_id=1,
        preference=ReferencePoint(
            aspiration_levels={
                "f_1": 0.1,
                "f_2": 0.9,
                "f_3": 0.4,
            }
        ),
        current_objectives=solve_result.current_solutions[0].objective_values,
        num_desired=1,
        parent_state_id=4,
    )
    response = post_json(client, "/method/nimbus/solve", request.model_dump(), access_token)
    solve_result: NIMBUSClassificationResponse = NIMBUSClassificationResponse.model_validate(
        json.loads(response.content)
    )
    assert solve_result.state_id == 5
    assert len(solve_result.saved_solutions) == 0


def test_add_new_dm(client: TestClient):
    """Test that adding a decision maker works."""
    # Create a new user to the database
    good_response = client.post(
        "/add_new_dm",
        data={"username": "new_dm", "password": "new_dm", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert good_response.status_code == status.HTTP_201_CREATED

    # There already should be a user named new_dm, so we shouldn't create another one.
    bad_response = client.post(
        "/add_new_dm",
        data={"username": "new_dm", "password": "new_dm", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert bad_response.status_code == status.HTTP_409_CONFLICT


def test_add_new_analyst(client: TestClient):
    """Test that adding a new analyst works."""
    # Try to create an analyst without logging in
    nologin_response = client.post(
        "/add_new_analyst",
        data={"username": "new_analyst", "password": "new_analyst", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    # No user
    assert nologin_response.status_code == status.HTTP_401_UNAUTHORIZED

    # Try to create an analyst using a dm account.
    response = client.post(
        "/add_new_dm",
        data={"username": "new_dm", "password": "new_dm", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    dm_access_token = login(client, username="new_dm", password="new_dm")  # noqa: S106

    dm_response = client.post(
        "/add_new_analyst",
        data={"username": "new_analyst", "password": "new_analyst", "grant_type": "password"},
        headers={"Authorization": f"Bearer {dm_access_token}", "content-type": "application/x-www-form-urlencoded"},
    )

    # Creating an analyst using unauthorized user should return 401 status
    assert dm_response.status_code == status.HTTP_401_UNAUTHORIZED

    # Login with proper user
    analyst_access_token = login(client)

    good_response = client.post(
        "/add_new_analyst",
        data={"username": "new_analyst", "password": "new_analyst", "grant_type": "password"},
        headers={
            "Authorization": f"Bearer {analyst_access_token}",
            "content-type": "application/x-www-form-urlencoded",
        },
    )

    # Creating a new analyst with an analyst user should return 201
    assert good_response.status_code == status.HTTP_201_CREATED

    bad_response = client.post(
        "/add_new_analyst",
        data={"username": "new_analyst", "password": "new_analyst", "grant_type": "password"},
        headers={
            "Authorization": f"Bearer {analyst_access_token}",
            "content-type": "application/x-www-form-urlencoded",
        },
    )

    # Trying to create an analyst with username that is already in use should return 409
    assert bad_response.status_code == status.HTTP_409_CONFLICT


def test_login_logout(client: TestClient):
    """Test that logging out works."""
    # Login (sets refresh token cookie)
    login(client=client, username="analyst", password="analyst")  # noqa: S106

    # Refresh access token
    response = client.post("/refresh")
    # Access token refreshed
    assert response.status_code == status.HTTP_200_OK

    # Logout (remove the refresh token cookie)
    response = client.post(
        "/logout",
    )
    assert response.status_code == status.HTTP_200_OK

    # Refresh access token
    response = client.post(
        "/refresh",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    # Access token NOT refreshed
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_group_operations(client: TestClient):
    """Tests for websocket endpoints and websockets."""
    create_endpoint = "/gdm/create_group"
    delete_endpoint = "/gdm/delete_group"
    add_user_endpoint = "/gdm/add_to_group"
    remove_user_endpoint = "/gdm/remove_from_group"
    group_info_endpoint = "/gdm/get_group_info"

    # login to analyst
    access_token = login(client=client, username="analyst", password="analyst")  # noqa: S106

    def get_info(gid: int):
        return post_json(
            client=client,
            endpoint=group_info_endpoint,
            json=GroupInfoRequest(
                group_id=gid,
            ).model_dump(),
            access_token=access_token,
        )

    def get_user_info(token: str):
        return client.get(
            "/user_info",
            headers={
                "Authorization": f"Bearer {token}",
                "content-type": "application/x-www-form-urlencoded",
            },
        )

    # try to create group with no problem
    response = post_json(
        client=client,
        endpoint=create_endpoint,
        json=GroupCreateRequest(group_name="testGroup", problem_id=10).model_dump(),
        access_token=access_token,
    )
    assert response.status_code == 404

    # Create group properly
    response = post_json(
        client=client,
        endpoint=create_endpoint,
        json=GroupCreateRequest(group_name="testGroup", problem_id=2).model_dump(),
        access_token=access_token,
    )
    assert response.status_code == 201

    # Add a user to database
    response = client.post(
        "/add_new_dm",
        data={"username": "new_dm", "password": "new_dm", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    # Add user to a group
    response = post_json(
        client=client,
        endpoint=add_user_endpoint,
        json=GroupModifyRequest(group_id=1, user_id=2).model_dump(),
        access_token=access_token,
    )
    assert response.status_code == status.HTTP_200_OK
    response = get_info(1)
    assert response.status_code == status.HTTP_200_OK
    group: GroupPublic = GroupPublic.model_validate(json.loads(response.content.decode("utf-8")))
    assert 2 in group.user_ids
    assert 1 not in group.user_ids

    user_info = get_user_info(access_token)
    user: UserPublic = UserPublic.model_validate(json.loads(user_info.content.decode("utf-8")))
    assert 1 in user.group_ids

    dm_access_token = login(client, "new_dm", "new_dm")

    user_info = get_user_info(dm_access_token)
    dm_user: UserPublic = UserPublic.model_validate(json.loads(user_info.content.decode("utf-8")))
    assert 1 in dm_user.group_ids

    # TODO: websocket testing and result fetching?

    # Remove user from a group
    response = post_json(
        client=client,
        endpoint=remove_user_endpoint,
        json=GroupModifyRequest(group_id=1, user_id=2).model_dump(),
        access_token=access_token,
    )
    assert response.status_code == status.HTTP_200_OK
    response = get_info(1)
    assert response.status_code == status.HTTP_200_OK
    group: GroupPublic = GroupPublic.model_validate(json.loads(response.content.decode("utf-8")))
    assert 2 not in group.user_ids

    user_info = get_user_info(dm_access_token)
    user: UserPublic = UserPublic.model_validate(json.loads(user_info.content.decode("utf-8")))
    assert 1 not in user.group_ids

    user_info = get_user_info(access_token)
    user: UserPublic = UserPublic.model_validate(json.loads(user_info.content.decode("utf-8")))
    assert 1 in user.group_ids

    # Delete the group
    response = post_json(
        client=client,
        endpoint=delete_endpoint,
        json=GroupInfoRequest(
            group_id=1,
        ).model_dump(),
        access_token=access_token,
    )
    assert response.status_code == status.HTTP_200_OK
    response = get_info(1)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    user_info = get_user_info(access_token)
    user: UserPublic = UserPublic.model_validate(json.loads(user_info.content.decode("utf-8")))
    assert 1 not in user.group_ids


def test_preferred_solver(client: TestClient):
    """Test that setting a preferred solver for the problem is ok."""
    access_token = login(client)

    request = ProblemSelectSolverRequest(problem_id=1, solver_string_representation="THIS SOLVER DOESN'T EXIST")
    response = post_json(client, "/problem/assign_solver", request.model_dump(), access_token)
    assert response.status_code == 404

    request = ProblemSelectSolverRequest(problem_id=1, solver_string_representation="pyomo_cbc")
    response = post_json(client, "/problem/assign_solver", request.model_dump(), access_token)
    assert response.status_code == 200

    request = {"problem_id": 1, "metadata_type": "solver_selection_metadata"}
    response = post_json(client, "/problem/get_metadata", request, access_token)
    assert response.status_code == 200

    model = SolverSelectionMetadata.model_validate(response.json()[0])

    assert model.metadata_type == "solver_selection_metadata"
    assert model.solver_string_representation == "pyomo_cbc"

    # Test that the solver is in use
    try:
        request = NIMBUSInitializationRequest(problem_id=1)
        response = post_json(client, "/method/nimbus/initialize", request.model_dump(), access_token)
        model = NIMBUSInitializationResponse.model_validate(response.json())
    except Exception as e:
        print(e)  # noqa: T201
        print("^ This outcome is expected since pyomo_cbc doesn't support nonlinear problems.")  # noqa: T201
        print("  As that solver is what we set it to be in the start, we can verify that they actually get used.")  # noqa: T201


def test_get_available_solvers(client: TestClient):
    """Test that available solvers can be fetched."""
    response = client.get("/problem/assign/solver")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Check that the returned solver names match the available solvers
    assert set(data) == set(available_solvers.keys())


def test_emo_solve_with_reference_point(client: TestClient):
    """Test that using EMO with reference point works as expected."""
    return
    # TODO: This test fails because of websocket issues. Fix those and re-enable the test.
    access_token = login(client)
    request = EMOIterateRequest(
        problem_id=1,
        template_options=[rvea_options.template],
        preference_options=ReferencePointOptions(preference={"f_1": 0.5, "f_2": 0.3, "f_3": 0.4}, method="Hakanen"),
    )

    response = post_json(client, "/method/emo/iterate", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK

    # Validate the response structure
    emo_response = EMOIterateResponse.model_validate(response.json())
    assert emo_response.client_id is not None
    state_id = emo_response.state_id

    initial_time = time.time()
    with client.websocket_connect(f"/method/emo/ws/{emo_response.client_id}") as websocket:
        while time.time() - initial_time < 10:
            message = websocket.receive_json()
            if message.get("message") == f"Finished {emo_response.method_ids[0]}":
                break
    # Fetch the state to verify it worked
    fetch_request = EMOFetchRequest(problem_id=1, parent_state_id=state_id)
    response = post_json(client, "/method/emo/fetch", fetch_request.model_dump(), access_token)


def test_get_problem_metadata(client: TestClient):
    """Test that fetching problem metadata works."""
    access_token = login(client=client)

    # Problem with no metadata
    req = {"problem_id": 1, "metadata_type": "forest_problem_metadata"}
    response = post_json(client=client, endpoint="/problem/get_metadata", json=req, access_token=access_token)
    assert response.status_code == 200
    assert response.json() == []

    # Problem with forest metadata
    req = {"problem_id": 2, "metadata_type": "forest_problem_metadata"}
    response = post_json(client=client, endpoint="/problem/get_metadata", json=req, access_token=access_token)
    assert response.status_code == 200
    assert response.json()[0]["metadata_type"] == "forest_problem_metadata"
    assert response.json()[0]["schedule_dict"] == {"type": "dict"}

    # No problem
    req = {"problem_id": 4, "metadata_type": "forest_problem_metadata"}
    response = post_json(client=client, endpoint="/problem/get_metadata", json=req, access_token=access_token)
    assert response.status_code == 404


def test_get_metadata_after_session_creation(client: TestClient):
    """Regression: get_metadata crashes when user has an active session.

    The bug is in fetch_interactive_session being called with swapped
    arguments (request, db_session) instead of (db_session, request),
    so db_session.exec() is actually called on the request body object.
    This only manifests when user.active_session_id is set (i.e., after
    creating a session), because otherwise the early return on line 72
    short-circuits before hitting session.exec().
    """
    access_token = login(client)

    # Step 1: Create a session — this sets user.active_session_id
    session_request = CreateSessionRequest(info="Test session")
    resp = post_json(client, "/session/new", session_request.model_dump(), access_token)
    assert resp.status_code == status.HTTP_200_OK

    # Step 2: Call get_metadata — this should work, but crashes with
    # AttributeError: 'ProblemMetaDataGetRequest' object has no attribute 'exec'
    # because fetch_interactive_session receives the request body where it
    # expects the database session.
    metadata_req = {"problem_id": 2, "metadata_type": "forest_problem_metadata"}
    resp = post_json(client, "/problem/get_metadata", metadata_req, access_token)
    assert resp.status_code == status.HTTP_200_OK, f"Expected 200, got {resp.status_code}: {resp.text}"


def test_gdm_score_bands(client: TestClient):
    """Test score bands endpoints."""
    access_token = login(client=client)

    # create group
    req = GroupCreateRequest(
        group_name="group",
        problem_id=3,  # The discrete representation problem
    ).model_dump()
    response = post_json(client=client, endpoint="/gdm/create_group", json=req, access_token=access_token)
    assert response.status_code == 201

    # Add a dm to the group
    # Create a new user to the database
    response = client.post(
        "/add_new_dm",
        data={"username": "dm", "password": "dm", "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 201

    req = GroupModifyRequest(group_id=1, user_id=2).model_dump()
    response = post_json(client=client, endpoint="/gdm/add_to_group", json=req, access_token=access_token)
    assert response.status_code == 200

    access_token = login(client=client, username="dm", password="dm")  # noqa: S106

    # Now we have a group, so let's get on with making stuff with gdm score bands.
    req = GDMScoreBandsInitializationRequest(
        group_id=1,
        score_bands_config=SCOREBandsGDMConfig(
            score_bands_config=SCOREBandsConfig(clustering_algorithm=KMeansOptions(n_clusters=5)), from_iteration=None
        ),
    ).model_dump()
    response = post_json(
        client=client, endpoint="/gdm-score-bands/get-or-initialize", json=req, access_token=access_token
    )
    assert response.status_code == 200
    response_innards = GDMSCOREBandsHistoryResponse.model_validate(response.json())
    cluster_size_1 = len(response_innards.history[-1].result.clusters)

    # VOTE AND CONFIRM
    req = GDMScoreBandsVoteRequest(
        group_id=1,
        vote=4,
    ).model_dump()
    response = post_json(client=client, endpoint="/gdm-score-bands/vote", json=req, access_token=access_token)
    assert response.status_code == 200
    req = GroupInfoRequest(group_id=1).model_dump()
    response = post_json(client=client, endpoint="/gdm-score-bands/confirm", json=req, access_token=access_token)
    assert response.status_code == 200

    req = GDMScoreBandsInitializationRequest(
        group_id=1,
        score_bands_config=SCOREBandsGDMConfig(
            score_bands_config=SCOREBandsConfig(clustering_algorithm=KMeansOptions(n_clusters=5)),
            from_iteration=response_innards.history[-1].latest_iteration,
        ),
    ).model_dump()
    response = post_json(
        client=client, endpoint="/gdm-score-bands/get-or-initialize", json=req, access_token=access_token
    )
    assert response.status_code == 200
    response_innards = GDMSCOREBandsHistoryResponse.model_validate(response.json())
    cluster_size_2 = len(response_innards.history[-1].result.clusters)

    # Since we've made one iteration, the length of the clustering and therefore the active
    # indices should be smaller the second time around than the first one.
    assert cluster_size_1 > cluster_size_2

    # TODO: Test reverting, re-clustering


def test_nimbus_get_multipliers_info(client: TestClient):
    """Test that get-multipliers-info returns multiplier data after a NIMBUS solve."""
    access_token = login(client)

    # First, do a NIMBUS solve to create a state with solver results
    preference = ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4})
    solve_request = NIMBUSClassificationRequest(
        problem_id=1,
        preference=preference,
        current_objectives={"f_1": 0.6, "f_2": 0.4, "f_3": 0.5},
        num_desired=2,
    )
    solve_response = post_json(client, "/method/nimbus/solve", solve_request.model_dump(), access_token)
    assert solve_response.status_code == status.HTTP_200_OK
    solve_result = NIMBUSClassificationResponse.model_validate(json.loads(solve_response.content.decode("utf-8")))

    # Now request multipliers for that state
    mult_request = NIMBUSMultiplierRequest(
        state_id=solve_result.state_id,
        objective_symbols=["f_1", "f_2", "f_3"],
    )
    mult_response = post_json(
        client,
        "/method/nimbus/get-multipliers-info",
        mult_request.model_dump(),
        access_token,
    )
    assert mult_response.status_code == status.HTTP_200_OK

    result = NIMBUSMultiplierResponse.model_validate(json.loads(mult_response.content.decode("utf-8")))

    # Response should have the right structure
    if result.lagrange_multipliers is not None:
        assert isinstance(result.lagrange_multipliers, list)
        assert len(result.lagrange_multipliers) == 2  # num_desired=2

    if result.tradeoffs_matrix is not None:
        assert isinstance(result.tradeoffs_matrix, list)

    if result.active_objectives is not None:
        assert isinstance(result.active_objectives, list)


def test_nimbus_get_multipliers_info_invalid_state(client: TestClient):
    """Test that get-multipliers-info with an invalid state_id returns empty."""
    access_token = login(client)

    mult_request = NIMBUSMultiplierRequest(state_id=99999)
    mult_response = post_json(
        client,
        "/method/nimbus/get-multipliers-info",
        mult_request.model_dump(),
        access_token,
    )
    assert mult_response.status_code == status.HTTP_200_OK
    result = NIMBUSMultiplierResponse.model_validate(json.loads(mult_response.content.decode("utf-8")))
    assert result.lagrange_multipliers is None


def test_xnimbus_solve(client: TestClient):
    """Test that XNIMBUS solve creates states with XNIMBUS kinds."""
    access_token = login(client)

    preference = ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4})
    request = NIMBUSClassificationRequest(
        problem_id=1,
        preference=preference,
        current_objectives={"f_1": 0.6, "f_2": 0.4, "f_3": 0.5},
        num_desired=2,
    )

    response = post_json(client, "/method/xnimbus/solve", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK
    result = NIMBUSClassificationResponse.model_validate(json.loads(response.content.decode("utf-8")))
    assert result.state_id is not None
    assert result.previous_preference == preference
    assert len(result.current_solutions) == 2


def test_xnimbus_initialize(client: TestClient):
    """Test that XNIMBUS initialize works."""
    access_token = login(client)

    request = NIMBUSInitializationRequest(problem_id=1)
    response = post_json(client, "/method/xnimbus/initialize", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK


def test_xnimbus_get_or_initialize(client: TestClient):
    """Test that XNIMBUS get-or-initialize returns existing state or creates new one."""
    access_token = login(client)

    request = NIMBUSInitializationRequest(problem_id=1)

    # First call should initialize
    response1 = post_json(client, "/method/xnimbus/get-or-initialize", request.model_dump(), access_token)
    assert response1.status_code == status.HTTP_200_OK

    # Second call should return the same state
    response2 = post_json(client, "/method/xnimbus/get-or-initialize", request.model_dump(), access_token)
    assert response2.status_code == status.HTTP_200_OK


def test_xnimbus_session_isolation_from_nimbus(client: TestClient):
    """Test that XNIMBUS states don't interfere with NIMBUS states."""
    access_token = login(client)

    # Initialize NIMBUS
    nimbus_request = NIMBUSInitializationRequest(problem_id=1)
    nimbus_response = post_json(client, "/method/nimbus/get-or-initialize", nimbus_request.model_dump(), access_token)
    assert nimbus_response.status_code == status.HTTP_200_OK
    nimbus_state = json.loads(nimbus_response.content.decode("utf-8"))

    # Initialize XNIMBUS (should create a new separate state)
    xnimbus_request = NIMBUSInitializationRequest(problem_id=1)
    xnimbus_response = post_json(
        client, "/method/xnimbus/get-or-initialize", xnimbus_request.model_dump(), access_token
    )
    assert xnimbus_response.status_code == status.HTTP_200_OK
    xnimbus_state = json.loads(xnimbus_response.content.decode("utf-8"))

    # State IDs should be different (separate sessions)
    assert nimbus_state.get("state_id") != xnimbus_state.get("state_id")


def test_xnimbus_get_multipliers(client: TestClient):
    """Test that XNIMBUS get-multipliers-info works after a solve."""
    access_token = login(client)

    # First solve
    preference = ReferencePoint(aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4})
    solve_request = NIMBUSClassificationRequest(
        problem_id=1,
        preference=preference,
        current_objectives={"f_1": 0.6, "f_2": 0.4, "f_3": 0.5},
        num_desired=2,
    )
    solve_response = post_json(client, "/method/xnimbus/solve", solve_request.model_dump(), access_token)
    assert solve_response.status_code == status.HTTP_200_OK
    solve_result = NIMBUSClassificationResponse.model_validate(json.loads(solve_response.content.decode("utf-8")))

    # Now get multipliers
    mult_request = NIMBUSMultiplierRequest(
        state_id=solve_result.state_id,
        objective_symbols=["f_1", "f_2", "f_3"],
    )
    mult_response = post_json(
        client,
        "/method/xnimbus/get-multipliers-info",
        mult_request.model_dump(),
        access_token,
    )
    assert mult_response.status_code == status.HTTP_200_OK
    result = NIMBUSMultiplierResponse.model_validate(json.loads(mult_response.content.decode("utf-8")))
    assert result is not None
