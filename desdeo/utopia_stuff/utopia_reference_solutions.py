"""This is a docstring."""

import json

from desdeo.api.db import SessionLocal
from desdeo.api.db_models import Method, SolutionArchive, User, Utopia
from desdeo.api.db_models import Problem as ProblemInDB
from desdeo.api.schema import Methods
from desdeo.utopia_stuff.utopia_problem import utopia_problem


def get_chosen_solution(username: str):
    """Recreates the forest problem for the specified user.

    Args:
        username (str): username of the forest owner
    """
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise Exception("User not found")  # noqa: TRY002
    problem_in_db = (
        db.query(ProblemInDB).filter(ProblemInDB.owner == user.id, ProblemInDB.name == "Metsänhoitosuunnitelma").first()
    )
    # map_info = db.query(Utopia).filter(Utopia.problem == problem_in_db.id, Utopia.user == user.id)

    nimbus_method = db.query(Method).filter(Method.kind == Methods.NIMBUS).first()

    solution = (
        db.query(SolutionArchive)
        .filter(
            SolutionArchive.user == user.id,
            SolutionArchive.problem == problem_in_db.id,
            SolutionArchive.method == nimbus_method.id,
        )
        .first()
    )

    if not solution:
        return (None, None)

    return (solution.objectives, solution.decision_variables)


"""    with open("C:/MyTemp/data/forest_owners.json") as file:  # noqa: PTH123
        fo_dict = json.load(file)

    print(fo_dict[username])

    problem, schedule_dict = utopia_problem(
        simulation_results=fo_dict[username]["simulation_results"],
        treatment_key=fo_dict[username]["treatment_key"],
        problem_name="Metsänhoitosuunnitelma",
    )

    problem_in_db.value = problem.model_dump(mode="json")
    map_info.schedule_dict = schedule_dict

    db.commit()"""


if __name__ == "__main__":
    # print(get_chosen_solution("Iisakkila"))
    with open("C:/MyTemp/data/forest_owners.json") as file:  # noqa: PTH123
        fo_dict = json.load(file)

    reference_dict = {}
    for fo in fo_dict:
        objectives, decision_vars = get_chosen_solution(fo)
        if objectives is None:
            continue
        reference_dict[fo] = {
            "objectives": objectives,
            "decisions_vars": decision_vars,
            "simulation_results": fo_dict[fo]["simulation_results"],
        }

    with open("reference_solutions.json", "w") as file:
        json.dump(reference_dict, file, indent=4)  # indent=4 makes it nicely formatted
