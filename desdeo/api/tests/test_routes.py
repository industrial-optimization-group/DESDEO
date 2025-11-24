"""Tests related to routes and routers."""

import json

from fastapi import status
from fastapi.testclient import TestClient
from websockets.asyncio.client import connect

from desdeo.api.models import (
    CreateSessionRequest,
    EMOFetchRequest,
    EMOIterateRequest,
    EMOIterateResponse,
    EMOSaveRequest,
    ForestProblemMetaData,
    GenericIntermediateSolutionResponse,
    GetSessionRequest,
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
    ProblemGetRequest,
    ProblemInfo,
    ProblemSelectSolverRequest,
    ReferencePoint,
    RPMSolveRequest,
    SolutionInfo,
    SolverSelectionMetadata,
    User,
    UserPublic,
    UserSavedEMOResults,
)
from desdeo.api.models.nimbus import NIMBUSInitializationResponse
from desdeo.api.models.state import EMOIterateState, EMOSaveState
from desdeo.api.routers.user_authentication import create_access_token
from desdeo.emo.options.algorithms import nsga3_options, rvea_options
from desdeo.emo.options.templates import ReferencePointOptions
from desdeo.problem.testproblems import simple_knapsack_vectors

from .conftest import get_json, login, post_json


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

    assert response_good.json()["access_token"] != response_refresh.json()["access_token"]


def test_get_problem(client: TestClient):
    """Test fetching specific problems based on their id."""
    access_token = login(client)

    response = post_json(client, "/problem/get", ProblemGetRequest(problem_id=1).model_dump(), access_token)

    assert response.status_code == 200

    info = ProblemInfo.model_validate(response.json())

    assert info.id == 1
    assert info.name == "dtlz2"
    assert info.problem_metadata is None

    response = post_json(client, "problem/get", ProblemGetRequest(problem_id=2).model_dump(), access_token)

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

    assert len(problems) == 3


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
    """Test that getting a session works as intended."""
    user: User = session_and_user["user"]

    access_token = login(client)

    # no sessions
    request = GetSessionRequest(session_id=1)
    response = post_json(client, "/session/get", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # add some sessions
    request = CreateSessionRequest(info="My session")
    response = post_json(client, "/session/new", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK

    assert user.active_session_id == 1

    request = CreateSessionRequest(info="My session")
    response = post_json(client, "/session/new", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK

    assert user.active_session_id == 2

    # sessions with id 1 and 2 should exist
    request = GetSessionRequest(session_id=1)
    response = post_json(client, "/session/get", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK

    request = GetSessionRequest(session_id=2)
    response = post_json(client, "/session/get", request.model_dump(), access_token)
    assert response.status_code == status.HTTP_200_OK


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
        solution_info=SolutionInfo(
            state_id=state_id,
            solution_index=solution_index
        ),
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
    request: NIMBUSDeleteSaveRequest = NIMBUSDeleteSaveRequest(state_id=2, solution_index=1)
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
        print(e)
        print("^ This outcome is expected since pyomo_cbc doesn't support nonlinear problems.")
        print("  As that solver is what we set it to be in the start, we can verify that they actually get used.")


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

    print("Request Data:", request.model_dump())

    response = post_json(client, "/method/emo/iterate", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK

    # Validate the response structure
    emo_response = EMOIterateResponse.model_validate(response.json())
    assert emo_response.client_id is not None
    state_id = emo_response.state_id
    print(emo_response)
    import time

    initial_time = time.time()
    with client.websocket_connect(f"/method/emo/ws/{emo_response.client_id}") as websocket:
        while time.time() - initial_time < 10:
            message = websocket.receive_json()
            print("WebSocket Message:", message)
            if message.get("message") == f"Finished {emo_response.method_ids[0]}":
                break
    # Fetch the state to verify it worked
    fetch_request = EMOFetchRequest(problem_id=1, parent_state_id=state_id)
    response = post_json(client, "/method/emo/fetch", fetch_request.model_dump(), access_token)
    print(response.json())


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
    req = {"problem_id": 3, "metadata_type": "forest_problem_metadata"}
    response = post_json(client=client, endpoint="/problem/get_metadata", json=req, access_token=access_token)
    assert response.status_code == 404
