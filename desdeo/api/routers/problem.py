"""Defines end-points to access and manage problems."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    ForestProblemMetaData,
    ProblemDB,
    ProblemGetRequest,
    ProblemInfo,
    ProblemInfoSmall,
    ProblemMetaDataDB,
    ProblemMetaDataGetRequest,
    ProblemSelectSolverRequest,
    RepresentativeNonDominatedSolutions,
    SolverSelectionMetadata,
    User,
    UserRole,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.problem import Problem
from desdeo.tools.utils import available_solvers
from .utils import get_session_context, get_session_context_base, SessionContext

router = APIRouter(prefix="/problem")

def check_solver(problem_db: ProblemDB):
    """Check if a preferred solver is set in the metadata.

    Check if a preferred solver is set in the metadata.
    If it exist, fetch its constructor and return it. Otherwise return None.
    """
    metadata: ProblemMetaDataDB = problem_db.problem_metadata
    solver_metadata = None
    if metadata is not None:
        solver_metadata_list = [
            metadata for metadata in metadata.all_metadata if metadata.metadata_type == "solver_selection_metadata"
        ]
        if solver_metadata_list != []:
            solver_metadata = solver_metadata_list[-1]

    if solver_metadata is not None:
        solver = available_solvers[solver_metadata.solver_string_representation]["constructor"]
    else:
        solver = None
    return solver


# This is needed, because otherwise fields ending in an underscore fail to parse.
async def parse_problem_json(request: Request) -> Problem:
    """Helper function to pass by_name=True to model_validate when coercing the json object to a Problem object."""
    data: dict = await request.json()
    return Problem.model_validate(data, by_name=True)


@router.get("/all")
def get_problems(user: Annotated[User, Depends(get_current_user)]) -> list[ProblemInfoSmall]:
    """Get information on all the current user's problems.

    Args:
        user (Annotated[User, Depends): the current user.

    Returns:
        list[ProblemInfoSmall]: a list of information on all the problems.
    """
    return user.problems


@router.get("/all_info")
def get_problems_info(user: Annotated[User, Depends(get_current_user)]) -> list[ProblemInfo]:
    """Get detailed information on all the current user's problems.

    Args:
        user (Annotated[User, Depends): the current user.

    Returns:
        list[ProblemInfo]: a list of the detailed information on all the problems.
    """
    return user.problems

@router.post("/get")
def get_problem(
    request: ProblemGetRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> ProblemInfo:
    """Get the model of a specific problem.

    Args:
        request (ProblemGetRequest): the request containing the problem's id `problem_id`.
        context (Annotated[SessionContext, Depends): the session context.

    Raises:
        HTTPException: could not find a problem with the given id.

    Returns:
        ProblemInfo: detailed information on the requested problem.
    """
    # db_session = context.db_session
    problem_db = context.problem_db

    # Ensure problem exists
    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The problem with the requested id={request.problem_id} was not found.",
        )

    return problem_db

@router.post("/add")
def add_problem(
    request: Annotated[Problem, Depends(parse_problem_json)],
    context: Annotated[SessionContext, Depends(get_session_context_base)],
) -> ProblemInfo:
    """Add a newly defined problem to the database.

    Args:
        request (Problem): the JSON representation of the problem.
        context (Annotated[SessionContext, Depends): the session context.

    Note:
        Users with the role 'guest' may not add new problems.

    Raises:
        HTTPException: when any issue with defining the problem arises.

    Returns:
        ProblemInfo: the information about the problem added.
    """
    user = context.user
    db_session = context.db_session

    if user.role == UserRole.guest:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest users are not allowed to add new problems.",
        )

    try:
        problem_db = ProblemDB.from_problem(request, user=user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not add problem. Possible reason: {e!r}",
        ) from e

    db_session.add(problem_db)
    db_session.commit()
    db_session.refresh(problem_db)

    return problem_db

@router.post("/add_json")
def add_problem_json(
    json_file: UploadFile,
    context: Annotated[SessionContext, Depends(get_session_context_base)],
) -> ProblemInfo:
    """Adds a problem to the database based on its JSON definition.

    Args:
        json_file (UploadFile): a file in JSON format describing the problem.
        context (Annotated[SessionContext, Depends): the session context.

    Raises:
        HTTPException: if the provided `json_file` is empty.
        HTTPException: if the content in the provided `json_file` is not in JSON format.__annotations__

    Returns:
        ProblemInfo: a description of the added problem.
    """
    user = context.user
    db_session = context.db_session

    raw = json_file.file.read()

    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload.")

    try:
        json.loads(raw)  # extra validation
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON.") from e

    problem = Problem.model_validate_json(raw, by_name=True)
    problem_db = ProblemDB.from_problem(problem, user=user)

    db_session.add(problem_db)
    db_session.commit()
    db_session.refresh(problem_db)

    return problem_db

@router.post("/get_metadata")
def get_metadata(
    request: ProblemMetaDataGetRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> list[ForestProblemMetaData | RepresentativeNonDominatedSolutions | SolverSelectionMetadata]:
    """Fetch specific metadata for a specific problem.

    Fetch specific metadata for a specific problem. See all the possible
    metadata types from DESDEO/desdeo/api/models/problem.py Problem Metadata
    section.

    Args:
        request (MetaDataGetRequest): the requested metadata type.
        context (Annotated[SessionContext, Depends]): the session context.

    Returns:
        list[ForestProblemMetadata | RepresentativeNonDominatedSolutions]: list containing all the metadata
            defined for the problem with the requested metadata type. If no match is found,
            returns an empty list.
    """
    db_session = context.db_session

    problem_from_db = db_session.exec(
        select(ProblemDB).where(ProblemDB.id == request.problem_id)
    ).first()

    if problem_from_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {request.problem_id} not found!",
        )

    problem_metadata = problem_from_db.problem_metadata

    if problem_metadata is None:
        # no metadata define for the problem
        return []
    # metadata is defined, try to find matching types based on request
    return [
        metadata
        for metadata in problem_metadata.all_metadata
        if metadata.metadata_type == request.metadata_type
    ]

@router.get("/assign/solver", response_model=list[str])
def get_available_solvers() -> list[str]:
    """Return the list of available solver names."""
    return list(available_solvers.keys())

@router.post("/assign_solver")
def select_solver(
    request: ProblemSelectSolverRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> JSONResponse:
    """Assign a specific solver for a problem.

    Args:
        request: ProblemSelectSolverRequest: The request containing problem id and string representation of the solver
        context: Annotated[SessionContext, Depends(get_session)]: The session context.

    Raises:
        HTTPException: Unknown solver, unauthorized user

    Returns:
        JSONResponse: A simple confirmation.
    """
    db_session = context.db_session
    user = context.user

    # Validate solver type
    if request.solver_string_representation not in [x for x, _ in available_solvers.items()]:
        raise HTTPException(
            detail=f"Solver of unknown type: {request.solver_string_representation}",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Fetch problem
    problem_db = db_session.exec(
        select(ProblemDB).where(ProblemDB.id == request.problem_id)
    ).first()

    if problem_db is None:
        raise HTTPException(
            detail=f"No problem with ID {request.problem_id}!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Auth the user
    if user.id != problem_db.user_id:
        raise HTTPException(
            detail="Unauthorized user!",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # All good, get on with it.
    problem_metadata = problem_db.problem_metadata
    if problem_metadata is None:
        # There's no metadata for this problem! Create some.
        problem_metadata = ProblemMetaDataDB(problem_id=problem_db.id, problem=problem_db)
        db_session.add(problem_metadata)
        db_session.commit()
        db_session.refresh(problem_metadata)

    # Remove existing solver selection metadata
    if problem_metadata.solver_selection_metadata:
        db_session.delete(problem_metadata.solver_selection_metadata[-1])
        db_session.commit()

    # Add new solver selection metadata
    solver_selection_metadata = SolverSelectionMetadata(
        metadata_id=problem_metadata.id,
        solver_string_representation=request.solver_string_representation,
        metadata_instance=problem_metadata,
    )

    db_session.add(solver_selection_metadata)
    db_session.commit()
    db_session.refresh(solver_selection_metadata)

    problem_metadata.solver_selection_metadata.append(solver_selection_metadata)
    db_session.add(problem_metadata)
    db_session.commit()
    db_session.refresh(problem_metadata)

    return JSONResponse(content={"message": "OK"}, status_code=status.HTTP_200_OK)
