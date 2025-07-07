"""Router for evolutionary multiobjective optimization (EMO) methods."""

from typing import Dict, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlmodel import select

from desdeo.emo.hooks.archivers import NonDominatedArchive
from desdeo.emo.methods.EAs import nsga3, rvea
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
from desdeo.api.models.EMO import EMOResults, EMOSolveRequest, EMOState
from desdeo.emo.methods.bases import EMOResult

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

    def _serialize_state_for_db(state: EMOState) -> dict:
        """Convert EMOState to dictionary for database storage."""
        return state.model_dump()

    # Create DB state
    state = StateDB(
        problem_id=problem_db.id,
        preference_id=preference_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=_serialize_state_for_db(emo_state),
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return emo_state


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
