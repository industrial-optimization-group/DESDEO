"""Utility functions for EMO database operations."""

from typing import List
from sqlmodel import Session
from desdeo.api.models.archive import UserSavedEMOResults, UserSavedEMOSolutionDB
from desdeo.api.models.state import StateDB


def user_save_emo_solutions(
    state: StateDB,
    solutions: List[UserSavedEMOResults],
    user_id: int,
    session: Session,
    problem_id: int,
    session_id: int | None = None,
    method: str = "nsga3",
) -> List[UserSavedEMOSolutionDB]:
    """Save EMO solutions to the user's archive."""

    saved_solutions = []

    for solution in solutions:
        # Create database entry for each solution
        solution_db = UserSavedEMOSolutionDB(
            name=solution.name,
            user_id=user_id,
            problem_id=problem_id,
            state_id=state.id,
            session_id=session_id,
            variable_values=solution.variable_values,
            objective_values=solution.objective_values,
            constraint_values=solution.constraint_values,
            extra_func_values=solution.extra_func_values,
            method=method,
            generation=solution.generation,
            rank=solution.rank,
            crowding_distance=solution.crowding_distance,
        )

        session.add(solution_db)
        saved_solutions.append(solution_db)

    session.commit()

    # Refresh all saved solutions
    for solution_db in saved_solutions:
        session.refresh(solution_db)

    return saved_solutions
