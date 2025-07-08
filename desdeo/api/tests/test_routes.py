"""Tests related to routes and routers."""

from fastapi import status
from fastapi.testclient import TestClient

from desdeo.api.models import (
    CreateSessionRequest,
    GetSessionRequest,
    InteractiveSessionDB,
    NIMBUSClassificationRequest,
    NIMBUSSaveRequest,
    NIMBUSSaveState,
    ProblemGetRequest,
    ProblemInfo,
    ReferencePoint,
    RPMSolveRequest,
    User,
    PreferedSolutions,
    NonPreferredSolutions,
)
from desdeo.api.models.archive import UserSavedSolverResults, UserSavedEMOResults
from desdeo.api.models.generic import IntermediateSolutionRequest
from desdeo.api.routers.user_authentication import create_access_token
from desdeo.problem.testproblems import simple_knapsack_vectors
from desdeo.api.models.EMO import EMOSaveRequest, EMOSaveState, EMOSolveRequest, EMOState
from desdeo.api.models.preference import PreferredRanges


def login(
    client: TestClient, username="analyst", password="analyst"
) -> str:  # noqa: S107
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
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )


def get_json(client: TestClient, endpoint: str, access_token: str):
    """Makes a get request and returns the response."""
    return client.get(
        endpoint,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
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

    assert (
        response_good.json()["access_token"] != response_refresh.json()["access_token"]
    )


def test_get_problem(client: TestClient):
    """Test fetching specific problems based on their id."""
    access_token = login(client)

    response = post_json(
        client,
        "/problem/get",
        ProblemGetRequest(problem_id=1).model_dump(),
        access_token,
    )

    assert response.status_code == 200

    info = ProblemInfo.model_validate(response.json())

    assert info.id == 1
    assert info.name == "dtlz2"

    response = post_json(
        client,
        "problem/get",
        ProblemGetRequest(problem_id=2).model_dump(),
        access_token,
    )

    assert response.status_code == 200

    info = ProblemInfo.model_validate(response.json())

    assert info.id == 2
    assert info.name == "The river pollution problem"


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
        problem_id=1,
        preference=ReferencePoint(
            aspiration_levels={"f_1": 0.5, "f_2": 0.3, "f_3": 0.4}
        ),
    )

    response = post_json(
        client, "/method/rpm/solve", request.model_dump(), access_token
    )

    assert response.status_code == status.HTTP_200_OK


def test_nimbus_solve(client: TestClient):
    """Test that using the NIMBUS method works as expected."""
    access_token = login(client)

    request = NIMBUSClassificationRequest(
        problem_id=1,
        preference=ReferencePoint(
            aspiration_levels={"f_1": 0.5, "f_2": 0.6, "f_3": 0.4}
        ),
        current_objectives={"f_1": 0.6, "f_2": 0.4, "f_3": 0.5},
    )

    response = post_json(
        client, "/method/nimbus/solve", request.model_dump(), access_token
    )
    assert response.status_code == status.HTTP_200_OK


def test_intermediate_solve(client: TestClient):
    """Test that solving intermediate solutions works as expected."""
    access_token = login(client)

    request = IntermediateSolutionRequest(
        problem_id=1,
        reference_solution_1={
            "x_1": 0.2,
            "x_2": 0.3,
            "x_3": 0.1,
            "x_4": 0.1,
            "x_5": 0.1,
        },
        reference_solution_2={
            "x_1": 0.5,
            "x_2": 0.6,
            "x_3": 0.4,
            "x_4": 0.1,
            "x_5": 0.1,
        },
    )

    response = post_json(
        client, "/method/generic/intermediate", request.model_dump(), access_token
    )
    assert response.status_code == status.HTTP_200_OK


def test_save_solution(client: TestClient):
    """Test that saving solutions works as expected."""
    # Login to get access token
    access_token = login(client)

    # Create test solutions with proper dictionary values
    variable_values = {"x_1": 0.3, "x_2": 0.8, "x_3": 0.1, "x_4": 0.6, "x_5": 0.9}
    objective_values = {"f_1": 1.2, "f_2": 0.9, "f_3": 1.5}
    constraint_values = {"g_1": 0.1}
    extra_func_values = {"extra_1": 5000, "extra_2": 600000}
    solution_name = "The most environment friendly solution"

    test_solutions = [
        UserSavedSolverResults(
            name=solution_name,
            optimal_variables=variable_values,
            optimal_objectives=objective_values,
            constraint_values=constraint_values,
            extra_func_values=extra_func_values,
            success=True,
            message="This is a test solution saved from the NIMBUS method.",
        )
    ]

    # Create the save request
    save_request = NIMBUSSaveRequest(
        problem_id=1,
        solutions=test_solutions,
    )

    # Make the request
    response = post_json(
        client, "/method/nimbus/save", save_request.model_dump(), access_token
    )

    # Verify the response and state
    assert response.status_code == status.HTTP_200_OK
    save_state = NIMBUSSaveState.model_validate(response.json())
    assert len(save_state.solver_results) == 1

    # Verify state contains solver results without name
    saved_result = save_state.solver_results[0]
    assert saved_result.optimal_variables == variable_values
    assert saved_result.optimal_objectives == objective_values
    assert saved_result.constraint_values == constraint_values
    assert saved_result.extra_func_values == extra_func_values
    assert not hasattr(saved_result, "name")  # Name should not be in state


def test_add_new_dm(client: TestClient):
    """Test that adding a decision maker works"""

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
    """Test that adding a new analyst works"""

    # Try to create an analyst without logging in
    nologin_response = client.post(
        "/add_new_analyst",
        data={
            "username": "new_analyst",
            "password": "new_analyst",
            "grant_type": "password",
        },
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

    dm_access_token = login(client, username="new_dm", password="new_dm")

    dm_response = client.post(
        "/add_new_analyst",
        data={
            "username": "new_analyst",
            "password": "new_analyst",
            "grant_type": "password",
        },
        headers={
            "Authorization": f"Bearer {dm_access_token}",
            "content-type": "application/x-www-form-urlencoded",
        },
    )

    # Creating an analyst using unauthorized user should return 401 status
    assert dm_response.status_code == status.HTTP_401_UNAUTHORIZED

    # Login with proper user
    analyst_access_token = login(client)

    good_response = client.post(
        "/add_new_analyst",
        data={
            "username": "new_analyst",
            "password": "new_analyst",
            "grant_type": "password",
        },
        headers={
            "Authorization": f"Bearer {analyst_access_token}",
            "content-type": "application/x-www-form-urlencoded",
        },
    )

    # Creating a new analyst with an analyst user should return 201
    assert good_response.status_code == status.HTTP_201_CREATED

    bad_response = client.post(
        "/add_new_analyst",
        data={
            "username": "new_analyst",
            "password": "new_analyst",
            "grant_type": "password",
        },
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
    login(client=client, username="analyst", password="analyst")

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


def test_nsga3_solve_with_reference_point(client: TestClient):
    """Test that using NSGA-III with reference point works as expected."""
    access_token = login(client)

    request = EMOSolveRequest(
        problem_id=1,
        method="nsga3",
        preference=ReferencePoint(
            aspiration_levels={"f_1_min": 0.5, "f_2_min": 0.3, "f_3_min": 0.4}
        ),
        max_evaluations=1000,
        number_of_vectors=20,
        use_archive=True,
    )

    print("Request Data:", request.model_dump())

    response = post_json(
        client, "/method/nsga3/solve", request.model_dump(), access_token
    )

    # Debug output
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Body: {response.json()}")
    print(f"Request Data: {request.model_dump()}")

    assert response.status_code == status.HTTP_200_OK

    # Validate the response structure
    emo_state = EMOState.model_validate(response.json())
    assert emo_state.method == "NSGAIII"
    assert emo_state.max_evaluations == 1000
    assert emo_state.number_of_vectors == 20
    assert emo_state.use_archive is True
    assert emo_state.results is not None
    assert len(emo_state.results.solutions) > 0
    assert len(emo_state.results.outputs) > 0


def test_nsga3_save_solutions(client: TestClient):
    """Test saving selected EMO solutions."""
    access_token = login(client)

    request = EMOSolveRequest(
        problem_id=1,
        method="nsga3",
        preference=ReferencePoint(
            aspiration_levels={"f_1_min": 0.5, "f_2_min": 0.3, "f_3_min": 0.4}
        ),
        max_evaluations=1000,
        number_of_vectors=20,
        use_archive=True,
    )

    print("Request Data:", request.model_dump())

    response = post_json(
        client, "/method/nsga3/solve", request.model_dump(), access_token
    )

    assert response.status_code == status.HTTP_200_OK

    # Validate the response structure
    emo_state = EMOState.model_validate(response.json())

    solutions = emo_state.results.solutions
    outputs = emo_state.results.outputs

    # Select first 2 solutions to save
    selected_solutions = []
    for i in range(min(2, len(solutions))):
        selected_solutions.append(
            UserSavedEMOResults(
                name="Selected Solution",
                optimal_variables={'x_1': 0.3625950577165081, 'x_2': 0.5014621638728629, 'x_3': 0.5133986403602678, 'x_4': 0.4971694793667669, 'x_5': 0.4977880432562051},
                optimal_objectives={'f_1_min': 0.6665403105011645, 'f_2_min': 0.4260369452661199, 'f_3_min': 0.6126011822203475},
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
    response = post_json(
        client,
        "/method/nsga3/save",
        save_request.model_dump(),
        access_token
    )

   # Verify the response and state
    assert response.status_code == status.HTTP_200_OK
    print("Save Response:", response.json())
    save_state = EMOSaveState.model_validate(response.json())
    #assert len(save_state.solver_results) == 1

    # Verify state contains solver results without name
    saved_result = save_state.saved_solutions[0]
    assert not hasattr(saved_result, "name")  # Name should not be in state


    # Get saved solutions
    saved_response = client.get(
        "/method/nsga3/saved-solutions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert saved_response.status_code == status.HTTP_200_OK
    saved_solutions = saved_response.json()
    assert len(saved_solutions) >= 2
