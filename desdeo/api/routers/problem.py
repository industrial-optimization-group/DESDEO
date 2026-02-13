"""Defines end-points to access and manage problems."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

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
from desdeo.api.models.representative_solution import (
    RepresentativeSolutionSetFull,
    RepresentativeSolutionSetInfo,
    RepresentativeSolutionSetRequest,
)
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.problem import Problem
from desdeo.tools.utils import available_solvers

from .utils import ContextField, SessionContext, SessionContextGuard

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
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]))],
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
    return context.problem_db


@router.post("/add")
def add_problem(
    request: Annotated[Problem, Depends(parse_problem_json)],
    context: Annotated[SessionContext, Depends(SessionContextGuard())],
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
    context: Annotated[SessionContext, Depends(SessionContextGuard())],
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
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[]))],
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
    problem_db = context.db_session.get(ProblemDB, request.problem_id)
    if not problem_db:
        raise HTTPException(status_code=404, detail=f"Problem with ID {request.problem_id} not found!")

    problem_metadata = problem_db.problem_metadata

    if problem_metadata is None:
        # no metadata define for the problem
        return []
    # metadata is defined, try to find matching types based on request
    return [metadata for metadata in problem_metadata.all_metadata if metadata.metadata_type == request.metadata_type]


@router.get("/assign/solver", response_model=list[str])
def get_available_solvers() -> list[str]:
    """Return the list of available solver names."""
    return list(available_solvers.keys())


@router.post("/assign_solver")
def select_solver(
    request: ProblemSelectSolverRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]))],
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
    problem_db = context.problem_db  # guaranteed

    # Validate solver type
    if request.solver_string_representation not in [x for x, _ in available_solvers.items()]:
        raise HTTPException(
            detail=f"Solver of unknown type: {request.solver_string_representation}",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Auth the user
    if user.id != problem_db.user_id:
        raise HTTPException(
            detail="Unauthorized user!",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # All good, get on with it.
    problem_metadata = problem_db.problem_metadata or ProblemMetaDataDB(problem_id=problem_db.id, problem=problem_db)
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


@router.post("/add_representative_solution_set")
def add_representative_solution_set(
    request: RepresentativeSolutionSetRequest,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[ContextField.PROBLEM]))],
):
    """Add a new representative solution set as metadata to a problem.

    Args:
        request (RepresentativeSolutionSetRequest): The JSON body containing the
            details of the representative solution set (name, description, solution data, ideal, nadir).
        context (SessionContext): The session context providing the current user and database session.

    Raises:
        HTTPException: If problem not found or unauthorized user.

    Returns:
        RepresentativeSolutionSetInfo: information about the added set.
    """
    db_session: Session = context.db_session
    problem_db = context.problem_db

    problem_metadata = problem_db.problem_metadata or ProblemMetaDataDB(problem_id=problem_db.id, problem=problem_db)
    db_session.add(problem_metadata)
    db_session.commit()
    db_session.refresh(problem_metadata)

    # Add new representative solution set
    repr_metadata = RepresentativeNonDominatedSolutions(
        metadata_id=problem_metadata.id,
        name=request.name,
        description=request.description,
        solution_data=request.solution_data,
        ideal=request.ideal,
        nadir=request.nadir,
        metadata_instance=problem_metadata,
    )

    db_session.add(repr_metadata)
    db_session.commit()
    db_session.refresh(repr_metadata)

    return RepresentativeSolutionSetInfo(
        id=repr_metadata.id,
        problem_id=problem_db.id,
        name=repr_metadata.name,
        description=repr_metadata.description,
        ideal=repr_metadata.ideal,
        nadir=repr_metadata.nadir,
    )


@router.get("/all_representative_solution_sets/{problem_id}")
def get_all_representative_solution_sets(
    problem_id: int,
    context: Annotated[SessionContext, Depends(SessionContextGuard(require=[]))],
):
    """Get meta information about all representative solution sets for a given problem.

    Returns only name, description, ideal, and nadir for each set.
    """
    db_session: Session = context.db_session
    user = context.user

    # Fetch problem
    problem_db = db_session.get(ProblemDB, problem_id)
    if not problem_db:
        raise HTTPException(status_code=404, detail=f"Problem with ID {problem_id} not found.")

    # Check the user
    if problem_db.user_id != user.id:
        raise HTTPException(status_code=401, detail="Unauthorized user.")

    # Fetch metadata
    problem_metadata = problem_db.problem_metadata
    if not problem_metadata:
        return []

    # Build response
    return [
        RepresentativeSolutionSetInfo(
            id=rep.id,
            problem_id=problem_id,
            name=rep.name,
            description=rep.description,
            ideal=rep.ideal,
            nadir=rep.nadir,
        )
        for rep in problem_metadata.representative_nd_metadata
    ]


@router.get("/representative_solution_set/{set_id}")
def get_representative_solution_set(
    set_id: int,
    context: Annotated[SessionContext, Depends(SessionContextGuard())],
):
    """Fetch full information of a single representative solution set by its ID."""
    db_session: Session = context.db_session

    # Fetch the representative set
    repr_set = db_session.get(RepresentativeNonDominatedSolutions, set_id)
    if repr_set is None:
        raise HTTPException(status_code=404, detail=f"Representative set with ID {set_id} not found.")

    # Check the user
    if repr_set.metadata_instance.problem.user_id != context.user.id:
        raise HTTPException(status_code=401, detail="Unauthorized user.")

    # Return all fields as a dict
    return RepresentativeSolutionSetFull(
        id=repr_set.id,
        problem_id=repr_set.metadata_instance.problem_id,
        name=repr_set.name,
        description=repr_set.description,
        solution_data=repr_set.solution_data,
        ideal=repr_set.ideal,
        nadir=repr_set.nadir,
    )


@router.delete("/representative_solution_set/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_representative_solution_set(
    set_id: int,
    context: Annotated[SessionContext, Depends(SessionContextGuard())],
):
    """Delete a representative solution set by its ID."""
    db_session: Session = context.db_session
    user = context.user

    # Fetch the set
    repr_metadata = db_session.get(RepresentativeNonDominatedSolutions, set_id)
    if repr_metadata is None:
        raise HTTPException(status_code=404, detail=f"Representative solution set with ID {set_id} not found.")

    # Ensure the user owns the problem this set belongs to
    problem_metadata = repr_metadata.metadata_instance
    if problem_metadata.problem.user_id != user.id:
        raise HTTPException(status_code=401, detail="Unauthorized user.")

    # Delete the set
    db_session.delete(repr_metadata)
    db_session.commit()


@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(
    problem_id: int,
    context: Annotated[SessionContext, Depends(SessionContextGuard())],
):
    """Delete a problem by its ID."""
    db_session: Session = context.db_session
    user = context.user

    problem_db = db_session.get(ProblemDB, problem_id)
    if problem_db is None:
        raise HTTPException(status_code=404, detail=f"Problem with ID {problem_id} not found.")

    if problem_db.user_id != user.id:
        raise HTTPException(status_code=401, detail="Unauthorized user.")

    db_session.delete(problem_db)
    db_session.commit()


@router.get("/{problem_id}/json")
def get_problem_json(
    problem_id: int,
    context: Annotated[SessionContext, Depends(SessionContextGuard())],
) -> JSONResponse:
    """Return a Problem as a serialized JSON object suitable for download/re-upload."""
    db_session: Session = context.db_session
    user = context.user

    problem_db = db_session.get(ProblemDB, problem_id)
    if problem_db is None:
        raise HTTPException(status_code=404, detail=f"Problem with ID {problem_id} not found.")

    if problem_db.user_id != user.id:
        raise HTTPException(status_code=401, detail="Unauthorized user.")

    problem = Problem.from_problemdb(problem_db)
    return JSONResponse(content=json.loads(problem.model_dump_json()), status_code=status.HTTP_200_OK)
