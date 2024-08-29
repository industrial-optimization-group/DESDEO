from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from desdeo.api.db import get_db
from desdeo.api.db_models import Problem as ProblemInDB, UserProblemAccess
from desdeo.api.db_models import User as UserInDB
from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.schema import User, UserRole
from desdeo.problem.schema import Problem
from desdeo.problem.utils import get_ideal_dict, get_nadir_dict
from desdeo.api.utils.database import (
    database_dependency,
    select,
    filter_by
)

router = APIRouter(prefix="/problem")


class ProblemFormat(BaseModel):
    objective_names: list[str]
    variable_names: list[str]
    ideal: list[float]
    nadir: list[float]
    n_objectives: int
    n_variables: int
    n_constraints: int
    minimize: list[int]
    problem_name: str
    problem_type: str
    problem_id: int


@router.get("/access/all")
async def get_all_problems(
    db: Annotated[database_dependency, Depends()],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ProblemFormat]:
    """Get all problems for the current user.

    Args:
        db (_type_, optional): A database session. Defaults to Annotated[Session, Depends(get_db)].
        user (_type_, optional): The user details. Defaults to Annotated(User, Depends(get_current_user)).

    Returns:
        list[ProblemFormat]: A list of problems.
    """
    if user.role != UserRole.ANALYST:
        problems = await db.all(select(ProblemInDB).filter(ProblemInDB.role_permission.any(user.role)))
        if type(user) == User:
            extra_problems = await db.all(select(UserProblemAccess).filter_by(user_id = user.index))
            problems += extra_problems
    else:
        problems = await db.all(select(ProblemInDB))

    all_problems = {}
    for problem in problems:
        if type(problem) == UserProblemAccess:
            problem = problem.problem
        temp_problem: Problem = Problem.model_validate(problem.value)
        if problem.id in all_problems.keys():
            continue

        all_problems[problem.id] = (
            ProblemFormat(
                objective_names=[objective.name for objective in temp_problem.objectives],
                variable_names=[variable.name for variable in temp_problem.variables],
                ideal=[value for _, value in get_ideal_dict(temp_problem).items()],
                nadir=[value for _, value in get_nadir_dict(temp_problem).items()],
                n_objectives=len(temp_problem.objectives),
                n_variables=len(temp_problem.variables),
                n_constraints=len(temp_problem.constraints) if temp_problem.constraints else 0,
                minimize=[-1 if objective.maximize else 1 for objective in temp_problem.objectives],
                problem_name=temp_problem.name,
                problem_type=problem.kind,
                problem_id=problem.id,
            )
        )

    return list(all_problems.values())
