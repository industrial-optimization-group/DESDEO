"""Utilities related to handling the databse."""

from sqlmodel import Session

from desdeo.api.models.archive import UserSavedSolutionDB, UserSavedSolverResults, UserSavedEMOResults
from desdeo.api.models.state import StateDB


def user_save_solutions(
    state_db: StateDB,
    results: list[UserSavedSolverResults | UserSavedEMOResults],
    user_id: int,
    session: Session,
):
    """Save solutions to the user's archive and create new state in the database.

    Args:
        state_db: The state containing the solutions
        results: List of solutions to save
        user_id: ID of the user saving the solutions
        session: Database session
    """
    # Create archive entries for selected solutions
    for solution in results:
        archive_entry = UserSavedSolutionDB(
            name=solution.name if solution.name else None,
            variable_values=solution.optimal_variables,
            objective_values=solution.optimal_objectives,
            constraint_values=solution.constraint_values,
            extra_func_values=solution.extra_func_values,
            user_id=user_id,
            problem_id=state_db.problem_id,
            state=state_db,
        )
        session.add(archive_entry)
    # state is already set in UserSavedSolutionDB, so no need to add it explictly
    session.commit()
