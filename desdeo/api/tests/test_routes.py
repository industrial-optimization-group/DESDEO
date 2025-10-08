"""Tests related to routes and routers."""

import json

from fastapi import status
from fastapi.testclient import TestClient

from desdeo.api.models import (
    CreateSessionRequest,
    EMOSaveRequest,
    EMOSolveRequest,
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
from desdeo.api.models.state import EMOSaveState, EMOState
from desdeo.api.routers.user_authentication import create_access_token
from desdeo.problem.testproblems import simple_knapsack_vectors


def login(client: TestClient, username="analyst", password="analyst") -> str:  # noqa: S107
    """Login, returns the access token."""
    response_login = client.post(
        "/login",
        data={"username": username, "password": password, "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    ).json()

    return response_login["access_token"]


def post_json(client: TestClient, endpoint: str, json: dict, access_token: str):
    """Makes a post request and returns the response."""
    return client.post(
        endpoint,
        json=json,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )


def get_json(client: TestClient, endpoint: str, access_token: str):
    """Makes a get request and returns the response."""
    return client.get(
        endpoint,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )


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
    access_token = login(client)

    request = EMOSolveRequest(
        problem_id=1,
        method="NSGA3",  # Use uppercase method name consistently
        preference=ReferencePoint(aspiration_levels={"f_1_min": 0.5, "f_2_min": 0.3, "f_3_min": 0.4}),
        max_evaluations=1000,
        number_of_vectors=20,
        use_archive=True,
    )

    print("Request Data:", request.model_dump())

    response = post_json(client, "/method/emo/solve", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK

    # Validate the response structure
    emo_state = EMOState.model_validate(response.json())
    assert emo_state.method == "NSGA3"  # Method name is consistently uppercase
    assert emo_state.max_evaluations == 1000
    assert emo_state.number_of_vectors == 20
    assert emo_state.use_archive is True
    assert emo_state.solutions is not None
    assert emo_state.outputs is not None
    assert len(emo_state.solutions) > 0
    assert len(emo_state.outputs) > 0


def test_emo_save_solutions(client: TestClient):
    """Test saving selected EMO solutions."""
    access_token = login(client)

    request = EMOSolveRequest(
        problem_id=1,
        method="NSGA3",  # Use uppercase method name consistently
        preference=ReferencePoint(aspiration_levels={"f_1_min": 0.5, "f_2_min": 0.3, "f_3_min": 0.4}),
        max_evaluations=1000,
        number_of_vectors=20,
        use_archive=True,
    )

    print("Request Data:", request.model_dump())

    response = post_json(client, "/method/emo/solve", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK

    # Validate the response structure
    emo_state = EMOState.model_validate(response.json())

    solutions = emo_state.solutions

    # Select first 2 solutions to save
    selected_solutions = []
    for _ in range(min(2, len(solutions))):
        selected_solutions.append(
            UserSavedEMOResults(
                name="Selected Solution",
                optimal_variables={
                    "x_1": 0.3625950577165081,
                    "x_2": 0.5014621638728629,
                    "x_3": 0.5133986403602678,
                    "x_4": 0.4971694793667669,
                    "x_5": 0.4977880432562051,
                },
                optimal_objectives={
                    "f_1_min": 0.6665403105011645,
                    "f_2_min": 0.4260369452661199,
                    "f_3_min": 0.6126011822203475,
                },
                constraint_values={},
                extra_func_values={},
            )
        )

    # Create the save request
    save_request = EMOSaveRequest(
        problem_id=1,
        solutions=selected_solutions,
    )

    # Make the request
    response = post_json(client, "/method/emo/save", save_request.model_dump(), access_token)

    # Verify the response and state
    assert response.status_code == status.HTTP_200_OK
    print("Save Response:", response.json())
    save_state = EMOSaveState.model_validate(response.json())
    # assert len(save_state.solver_results) == 1

    # Verify state contains solver results without name
    saved_result = save_state.saved_solutions[0]
    assert not hasattr(saved_result, "name")  # Name should not be in state

    # Get saved solutions
    saved_response = client.get(
        "/method/emo/saved-solutions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert saved_response.status_code == status.HTTP_200_OK
    saved_solutions = saved_response.json()
    assert len(saved_solutions) >= 2


def test_emo_solve_with_rvea(client: TestClient):
    """Test that using EMO with RVEA method works as expected."""
    access_token = login(client)

    request = EMOSolveRequest(
        problem_id=1,
        method="RVEA",  # Test RVEA method with uppercase
        preference=ReferencePoint(aspiration_levels={"f_1_min": 0.5, "f_2_min": 0.3, "f_3_min": 0.4}),
        max_evaluations=1000,
        number_of_vectors=20,
        use_archive=True,
    )

    response = post_json(client, "/method/emo/solve", request.model_dump(), access_token)

    assert response.status_code == status.HTTP_200_OK

    # Validate the response structure
    emo_state = EMOState.model_validate(response.json())
    assert emo_state.method == "RVEA"  # Method name is consistently uppercase
    assert emo_state.max_evaluations == 1000
    assert emo_state.number_of_vectors == 20
    assert emo_state.use_archive is True
    assert emo_state.solutions is not None
    assert emo_state.outputs is not None
    assert len(emo_state.solutions) > 0
    assert len(emo_state.outputs) > 0


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
