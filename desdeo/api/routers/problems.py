from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from desdeo.api.db import get_db
from desdeo.api.db_models import Problem as ProblemInDB
from desdeo.api.db_models import User as UserInDB
from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.schema import User
from desdeo.problem.schema import Problem
from desdeo.problem.utils import get_ideal_dict, get_nadir_dict

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
def get_all_problems(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ProblemFormat]:
    """Get all problems for the current user.

    Args:
        db (_type_, optional): A database session. Defaults to Annotated[Session, Depends(get_db)].
        user (_type_, optional): The user details. Defaults to Annotated(User, Depends(get_current_user)).

    Returns:
        list[ProblemFormat]: A list of problems.
    """
    user_id = db.query(UserInDB).filter(UserInDB.username == user.username).first().id
    problems = db.query(ProblemInDB).filter(ProblemInDB.owner == user_id).all()

    all_problems = []
    for problem in problems:
        temp_problem: Problem = Problem.model_validate(problem.value)
        all_problems.append(
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

    return all_problems
