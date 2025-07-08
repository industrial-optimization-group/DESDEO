"""Router for evolutionary multiobjective optimization (EMO) methods."""

from typing import Dict, Annotated, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlmodel import select

from desdeo.api.utils.database import user_save_solutions
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
    EMOSaveRequest,
    EMOSolveRequest,
)

from desdeo.api.models.state import (
    NSGAIIIState,
    NSGAIIISaveState)

from desdeo.api.models.archive import (
    UserSavedEMOResults,
)
from desdeo.api.utils.emo_database import _convert_dataframe_to_dict_list

router = APIRouter(prefix="/method/nsga3", tags=["evolutionary"])

@router.post("/solve")
def start_emo_optimization(
    request: EMOSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> NSGAIIIState:
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
    emo_results = solver()

    # Convert DataFrames to dictionaries for solutions
    solutions_dict = _convert_dataframe_to_dict_list(
        getattr(emo_results, "solutions", None)
    )

    # Convert DataFrames to dictionaries for outputs
    outputs_dict = _convert_dataframe_to_dict_list(getattr(emo_results, "outputs", None))

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
    emo_state = NSGAIIIState(
        method="NSGAIII",
        max_evaluations=request.max_evaluations,
        number_of_vectors=request.number_of_vectors,
        use_archive=request.use_archive,
        solutions=solutions_dict,
        outputs=outputs_dict,
    )

    # Create DB state
    state = StateDB(
        problem_id=problem_db.id,
        preference_id=preference_db.id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=emo_state,  # Convert to dict for JSON serialization
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    return emo_state



@router.post("/save")
def save(
    request: EMOSaveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> EMOSaveRequest:
    """Save solutions."""
    if request.session_id is not None:
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == request.session_id)
        interactive_session = session.exec(statement)

        if interactive_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find interactive session with id={request.session_id}.",
            )
    else:
        # request.session_id is None:
        # use active session instead
        statement = select(InteractiveSessionDB).where(InteractiveSessionDB.id == user.active_session_id)

        interactive_session = session.exec(statement).first()

    # fetch parent state
    if request.parent_state_id is None:
        # parent state is assumed to be the last state added to the session.
        parent_state = (
            interactive_session.states[-1]
            if (interactive_session is not None and len(interactive_session.states) > 0)
            else None
        )

    else:
        # request.parent_state_id is not None
        statement = session.select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Could not find state with id={request.parent_state_id}"
            )

    # save solver results for state in SolverResults format just for consistency (dont save name field to state)
    save_state = NSGAIIISaveState(
        saved_solutions=[solution.to_emo_results() for solution in request.solutions]
    )

    # create DB state
    state = StateDB(
        problem_id=request.problem_id,
        session_id=interactive_session.id if interactive_session is not None else None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=save_state,
    )
    # save solutions to the user's archive and add state to the DB
    user_save_solutions(state, request.solutions, user.id, session)

    return save_state

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
