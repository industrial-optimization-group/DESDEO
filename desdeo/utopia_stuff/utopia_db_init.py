from desdeo.api.db_init import *
import json

with open("C:/MyTemp/code/users_and_passwords.json") as file:
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

    problem, schedule_dict = utopia_problem(problem_name=f"{name}n metsä", holding=holding_num)
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
        problem=problem_in_db.id, user=user.id, map_json=forest_map, schedule_dict=schedule_dict
    )
    db.add(map_info)

    problem_access = db_models.UserProblemAccess(
        user_id=user.id,
        problem_access=problem_in_db.id,
    )
    db.add(problem_access)

    db.commit()
    holding_num += 1
    if holding_num > 5:
        holding_num = 1


db.close()
