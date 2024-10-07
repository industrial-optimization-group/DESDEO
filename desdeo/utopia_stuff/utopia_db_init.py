import json  # noqa: D100

from desdeo.api.db_init import *  # noqa: F403
from desdeo.utopia_stuff.utopia_problem import utopia_problem

with open("C:/MyTemp/code/users_and_passwords.json") as file:  # noqa: PTH123
    userdict = json.load(file)

db = SessionLocal()

holding_num = 1
for name in userdict:
    print(name)
    user = db_models.User(
        username=name,
        password_hash=get_password_hash(userdict[name]),
        role=UserRole.DM,
        privilages=[],
        user_group="",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    problem, schedule_dict = utopia_problem_old(problem_name=f"{name}n metsä", holding=holding_num)
    problem_in_db = db_models.Problem(
        owner=user.id,
        name=f"{name}n metsä",
        kind=ProblemKind.CONTINUOUS,
        obj_kind=ObjectiveKind.ANALYTICAL,
        solver=Solvers.GUROBIPY,
        value=problem.model_dump(mode="json"),
    )
    db.add(problem_in_db)
    db.commit()
    db.refresh(problem_in_db)

    # The info about the map and decision alternatives now goes into the database
    with open(f"desdeo/utopia_stuff/data/{holding_num}.json") as f:  # noqa: PTH123
        forest_map = f.read()
    map_info = db_models.Utopia(
        problem=problem_in_db.id,
        user=user.id,
        map_json=forest_map,
        schedule_dict=schedule_dict,
        years=["2025", "2030", "2035"],
        stand_id_field="standnumbe",
        stand_descriptor="standnumbe",
    )
    db.add(map_info)

    problem_access = db_models.UserProblemAccess(
        user_id=user.id,
        problem_access=problem_in_db.id,
    )
    db.add(problem_access)

    db.commit()
    holding_num += 1
    if holding_num > 5:  # noqa: PLR2004
        holding_num = 1

# Actual forest owners start from here
# The contents of this file are not supposed to be found on github
"""
The json file contents look something like this
{
  "jane_smith": {
    "password": "password123",
    "simulation_results": "C:/MyTemp/data/alternatives/fake_location/alternatives.csv",
    "treatment_key": "C:/MyTemp/data/alternatives/fake_location/alternatives_key.csv",
    "mapjson": "C:/MyTemp/data/alternatives/fake_location/map.geojson",
    "stand_id": "id",
    "stand_descriptor": "number"
  }
}
"""
with open("C:/MyTemp/data/forest_owners.json") as file:  # noqa: PTH123
    fo_dict = json.load(file)

for name in fo_dict:
    print(name)
    user = db_models.User(
        username=name,
        password_hash=get_password_hash(fo_dict[name]["password"]),
        role=UserRole.DM,
        privilages=[],
        user_group="",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    problem, schedule_dict = utopia_problem(
        simulation_results=fo_dict[name]["simulation_results"],
        treatment_key=fo_dict[name]["treatment_key"],
        problem_name=f"{name}n metsä",
    )
    problem_in_db = db_models.Problem(
        owner=user.id,
        name="Metsänhoitosuunnitelma",
        kind=ProblemKind.CONTINUOUS,
        obj_kind=ObjectiveKind.ANALYTICAL,
        solver=Solvers.GUROBIPY,
        value=problem.model_dump(mode="json"),
    )
    db.add(problem_in_db)
    db.commit()
    db.refresh(problem_in_db)

    # The info about the map and decision alternatives now goes into the database
    with open(fo_dict[name]["mapjson"]) as f:  # noqa: PTH123
        forest_map = f.read()
    map_info = db_models.Utopia(
        problem=problem_in_db.id,
        user=user.id,
        map_json=forest_map,
        schedule_dict=schedule_dict,
        years=["5", "10", "20"],
        stand_id_field=fo_dict[name]["stand_id"],
        stand_descriptor=fo_dict[name]["stand_descriptor"],
    )
    db.add(map_info)

    problem_access = db_models.UserProblemAccess(
        user_id=user.id,
        problem_access=problem_in_db.id,
    )
    db.add(problem_access)

    db.commit()

db.close()
