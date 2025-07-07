"""Router for evolutionary multiobjective optimization (EMO) methods."""

from typing import Dict, Annotated, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlmodel import select

from desdeo.emo.hooks.archivers import NonDominatedArchive
from desdeo.emo.methods.EAs import nsga3
from desdeo.problem import Problem

from desdeo.api.db import get_session
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.models.preference import (
    PreferenceDB,
    PreferenceBase,
    ReferencePoint,
    PreferredRanges,
    PreferedSolutions,
    NonPreferredSolutions,
)
from desdeo.api.models.problem import ProblemDB
from desdeo.api.models.session import InteractiveSessionDB
from desdeo.api.models.state import StateDB
from desdeo.api.models.user import User
from desdeo.api.models.EMO import (
    EMOResults,
    EMOSaveRequest,
    EMOSaveState,
    EMOSolveRequest,
    EMOState,
)
from desdeo.api.models.archive import (
    NonDominatedArchiveDB,
    NonDominatedArchiveResponse,
    UserSavedEMOResults,
    UserSavedEMOSolutionResponse,
)
from desdeo.emo.methods.bases import EMOResult
from desdeo.api.utils.emo_database import user_save_emo_solutions

router = APIRouter(prefix="/method/nsga3", tags=["evolutionary"])


def _convert_dataframe_to_dict_list(df):
    """Convert DataFrame to list of dictionaries, handling different DataFrame types."""
    if df is None:
        return []

    # Check if it's a pandas DataFrame
    if hasattr(df, "iterrows"):
        return [row.to_dict() for _, row in df.iterrows()]

    # Check if it's a Polars DataFrame
    elif hasattr(df, "iter_rows"):
        # Get column names
        columns = df.columns
        return [dict(zip(columns, row)) for row in df.iter_rows()]

    # Check if it's already a list of dictionaries
    elif isinstance(df, list):
        return df

    # Check if it has to_dict method (pandas Series)
    elif hasattr(df, "to_dict"):
        return [df.to_dict()]

    # Try to convert to dict if it's a single row
    elif hasattr(df, "__iter__") and not isinstance(df, (str, dict)):
        try:
            # Assume it's iterable with column names
            if hasattr(df, "columns"):
                return [dict(zip(df.columns, row)) for row in df]
            else:
                # Generic conversion
                return [dict(enumerate(row)) for row in df]
        except Exception:
            pass

    # If all else fails, try to convert to string representation
    return [{"data": str(df)}]


@router.post("/solve", response_model=EMOState)
def start_emo_optimization(
    request: EMOSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> EMOState:
    """Start interactive evolutionary multiobjective optimization."""

    # Handle session logic
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement).first()

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # Use active session
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )
        interactive_session = session.exec(statement).first()

    # Fetch problem from DB
    statement = select(ProblemDB).where(
        ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id
    )
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
        )

    # Convert ProblemDB to Problem object
    problem = Problem.from_problemdb(problem_db)

    # Build reference vector options based on preference type
    reference_vector_options = _build_reference_vector_options(
        request.preference, request.number_of_vectors
    )

    # Create solver and publisher
    solver, publisher = nsga3(
        problem=problem, reference_vector_options=reference_vector_options
    )

    # Add archive if requested
    archive = None
    if request.use_archive:
        archive = NonDominatedArchive(problem=problem, publisher=publisher)
        publisher.auto_subscribe(archive)

    # Run optimization
    results = solver()

    # Convert DataFrames to dictionaries for solutions
    solutions_dict = _convert_dataframe_to_dict_list(
        getattr(results, "solutions", None)
    )

    # Convert DataFrames to dictionaries for outputs
    outputs_dict = _convert_dataframe_to_dict_list(getattr(results, "outputs", None))

    # Handle archive solutions if they exist - use archive variable, not results
    archive_solutions_dict = None
    if archive is not None and hasattr(archive, "solutions"):
        archive_solutions_dict = _convert_dataframe_to_dict_list(archive.solutions)

    # Create EMOResults object
    emo_results = EMOResults(
        solutions=solutions_dict,
        outputs=outputs_dict,  # This contains objectives, constraints, and targets
        archive_solutions=archive_solutions_dict,
        method=request.method,
        converged=getattr(results, "converged", False),
        iteration_count=getattr(results, "iteration_count", 1),
        archive_size=len(archive_solutions_dict) if archive_solutions_dict else None,
    )

    # Create DB preference
    preference_db = PreferenceDB(
        user_id=user.id, problem_id=problem_db.id, preference=request.preference
    )

    session.add(preference_db)
    session.commit()
    session.refresh(preference_db)

    # Handle parent state
    if request.parent_state_id is None:
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )
    else:
        statement = select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    # Create EMO state
    emo_state = EMOState(
        method="NSGAIII",
        max_evaluations=request.max_evaluations,
        number_of_vectors=request.number_of_vectors,
        use_archive=request.use_archive,
        results=emo_results,
    )

    # Create DB state
    state = StateDB(
        problem_id=problem_db.id,
        preference_id=preference_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=emo_state.model_dump(),  # Convert to dict for JSON serialization
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    # Save or update archive to database if it exists and we have a session
    if (
        archive is not None
        and hasattr(archive, "solutions")
        and archive_solutions_dict
        and interactive_session is not None
    ):

        _save_or_update_session_archive(
            session=session,
            interactive_session=interactive_session,
            archive=archive,
            archive_solutions_dict=archive_solutions_dict,
            outputs_dict=outputs_dict,
            request=request,
            user=user,
            state_id=state.id,
        )

    return emo_state


def _save_or_update_session_archive(
    session: Session,
    interactive_session,
    archive,
    archive_solutions_dict: list,
    outputs_dict: list,
    request: EMOSolveRequest,
    user: User,
    state_id: Optional[int] = None,
):
    """Save or update the archive for the current session."""

    # Check if archive already exists for this session
    existing_archive = session.exec(
        select(NonDominatedArchiveDB).where(
            NonDominatedArchiveDB.session_id == interactive_session.id
        )
    ).first()

    # Get archive objectives (try different attributes)
    archive_objectives = []
    if hasattr(archive, "objectives"):
        archive_objectives = _convert_dataframe_to_dict_list(archive.objectives)
    elif hasattr(archive, "outputs"):
        archive_objectives = _convert_dataframe_to_dict_list(archive.outputs)
    else:
        # Use outputs from results as fallback
        archive_objectives = outputs_dict

    # Prepare archive data
    archive_data = {
        "name": f"NSGA-III Archive - Session {interactive_session.id}",
        "method": request.method,
        "problem_id": request.problem_id,
        "user_id": user.id,
        "session_id": interactive_session.id,
        "state_id": state_id,
        "total_solutions": len(archive_solutions_dict),
        "generation_created": getattr(archive, "generation_created", 1),
        "max_evaluations": request.max_evaluations,
        "number_of_vectors": request.number_of_vectors,
        "solutions": archive_solutions_dict,
        "objectives": archive_objectives,
        "constraints": None,  # Add if available
        "preference_type": getattr(request.preference, "preference_type", None),
        "preference_data": (
            request.preference.model_dump()
            if hasattr(request.preference, "model_dump")
            else request.preference if isinstance(request.preference, dict) else None
        ),
        "created_at": datetime.utcnow(),
    }

    if existing_archive:
        # Update existing archive
        for key, value in archive_data.items():
            if key != "user_id":  # Don't update user_id
                setattr(existing_archive, key, value)

        session.commit()
        session.refresh(existing_archive)
        print(f"Updated existing archive for session {interactive_session.id}")
    else:
        # Create new archive
        new_archive = NonDominatedArchiveDB(**archive_data)
        session.add(new_archive)
        session.commit()
        session.refresh(new_archive)
        print(f"Created new archive for session {interactive_session.id}")


@router.post("/save", response_model=EMOSaveState)
def save_emo_solutions(
    request: EMOSaveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> EMOSaveState:
    """Save selected EMO solutions to user's archive."""

    # Handle session logic
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == request.session_id
        )
        interactive_session = session.exec(statement).first()

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # Use active session
        statement = select(InteractiveSessionDB).where(
            InteractiveSessionDB.id == user.active_session_id
        )
        interactive_session = session.exec(statement).first()

    # Fetch parent state
    if request.parent_state_id is None:
        # Parent state is assumed to be the last state added to the session
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )
    else:
        statement = select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    # Create save state (save solver results for state in EMOResults format)
    save_state = EMOSaveState(
        saved_solutions=request.solutions,
        total_saved=len(request.solutions),
        method="nsga3",
    )

    # Create DB state
    state = StateDB(
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state.model_dump(),
    )

    # Save solutions to the user's archive and add state to the DB
    user_save_emo_solutions(
        state=state,
        solutions=request.solutions,
        user_id=user.id,
        session=session,
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        method="nsga3",
    )

    return save_state


@router.get("/saved-solutions", response_model=List[UserSavedEMOSolutionResponse])
def get_user_saved_emo_solutions(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    problem_id: Optional[int] = None,
    session_id: Optional[int] = None,
    method: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[UserSavedEMOSolutionResponse]:
    """Get user's saved EMO solutions."""

    from desdeo.api.models.archive import UserSavedEMOSolutionDB

    query = select(UserSavedEMOSolutionDB).where(
        UserSavedEMOSolutionDB.user_id == user.id
    )

    if problem_id:
        query = query.where(UserSavedEMOSolutionDB.problem_id == problem_id)

    if session_id:
        query = query.where(UserSavedEMOSolutionDB.session_id == session_id)

    if method:
        query = query.where(UserSavedEMOSolutionDB.method == method)

    query = (
        query.offset(skip)
        .limit(limit)
        .order_by(UserSavedEMOSolutionDB.created_at.desc())
    )

    solutions = session.exec(query).all()
    return solutions


@router.delete("/saved-solutions/{solution_id}")
def delete_saved_emo_solution(
    solution_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Delete a saved EMO solution."""

    from desdeo.api.models.archive import UserSavedEMOSolutionDB

    solution = session.exec(
        select(UserSavedEMOSolutionDB).where(
            UserSavedEMOSolutionDB.id == solution_id,
            UserSavedEMOSolutionDB.user_id == user.id,
        )
    ).first()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Solution with id={solution_id} not found",
        )

    session.delete(solution)
    session.commit()

    return {"message": f"Solution {solution_id} deleted successfully"}


@router.put("/saved-solutions/{solution_id}/name")
def update_saved_emo_solution_name(
    solution_id: int,
    name: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> UserSavedEMOSolutionResponse:
    """Update the name of a saved EMO solution."""

    from desdeo.api.models.archive import UserSavedEMOSolutionDB

    solution = session.exec(
        select(UserSavedEMOSolutionDB).where(
            UserSavedEMOSolutionDB.id == solution_id,
            UserSavedEMOSolutionDB.user_id == user.id,
        )
    ).first()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Solution with id={solution_id} not found",
        )

    solution.name = name
    session.commit()
    session.refresh(solution)

    return solution


# Helper functions
def _build_reference_vector_options(
    preference: PreferenceBase, number_of_vectors: int
) -> Dict:
    """Build reference vector options based on preference type."""

    base_options = {
        "number_of_vectors": number_of_vectors,
    }

    # Convert the preference dict to the correct object type
    if isinstance(preference, dict):
        preference_type = preference.get("preference_type")
        if preference_type == "reference_point":
            from desdeo.api.models.preference import ReferencePoint

            preference = ReferencePoint.model_validate(preference)
        elif preference_type == "preferred_solutions":
            from desdeo.api.models.preference import PreferedSolutions

            preference = PreferedSolutions.model_validate(preference)
        elif preference_type == "non_preferred_solutions":
            from desdeo.api.models.preference import NonPreferredSolutions

            preference = NonPreferredSolutions.model_validate(preference)
        elif preference_type == "preferred_ranges":
            from desdeo.api.models.preference import PreferredRanges

            preference = PreferredRanges.model_validate(preference)

    # Now handle the properly typed preference object
    if hasattr(preference, "aspiration_levels"):
        base_options["interactive_adaptation"] = "reference_point"
        base_options["reference_point"] = preference.aspiration_levels
    elif hasattr(preference, "preferred_solutions"):
        base_options["interactive_adaptation"] = "preferred_solutions"
        base_options["preferred_solutions"] = preference.preferred_solutions
    elif hasattr(preference, "non_preferred_solutions"):
        base_options["interactive_adaptation"] = "non_preferred_solutions"
        base_options["non_preferred_solutions"] = preference.non_preferred_solutions
    elif hasattr(preference, "preferred_ranges"):
        base_options["interactive_adaptation"] = "preferred_ranges"
        base_options["preferred_ranges"] = preference.preferred_ranges
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported preference type: {type(preference)} with preference_type: {getattr(preference, 'preference_type', 'unknown')}",
        )

    return base_options
