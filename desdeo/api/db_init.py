"""This module initializes the database."""

import json
from os import walk
import warnings

import numpy as np
import polars as pl
from sqlalchemy import text
from sqlalchemy_utils import create_database, database_exists, drop_database

from desdeo.api import db_models
from desdeo.api.config import DBConfig
from desdeo.api.db import Base, SessionLocal, engine
from desdeo.api.routers.UserAuth import get_password_hash
from desdeo.api.schema import Methods, ObjectiveKind, ProblemKind, Solvers, UserPrivileges, UserRole
from desdeo.problem.schema import DiscreteRepresentation, Objective, Problem, Variable
from desdeo.problem.testproblems import (
    binh_and_korn,
    forest_problem,
    forest_problem_discrete,
    nimbus_test_problem,
    river_pollution_problem,
    river_pollution_problem_discrete,
    spanish_sustainability_problem,
    spanish_sustainability_problem_discrete,
)
from desdeo.utopia_stuff.utopia_problem_old import utopia_problem_old

TEST_USER = "test"
TEST_PASSWORD = "test"  # NOQA: S105 # TODO: Remove this line and create a proper user creation system.

# The following line creates the database and tables. This is not ideal, but it is simple for now.
# TODO: Remove this line and create a proper database migration system.
print("Creating database tables.")
if not database_exists(engine.url):
    create_database(engine.url)
else:
    warnings.warn("Database already exists. Clearing it.", stacklevel=1)

    # Drop all active connections
    db = SessionLocal()
    terminate_connections_sql = text("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = :db_name AND pid <> pg_backend_pid();
    """)
    db.execute(terminate_connections_sql, {"db_name": DBConfig.db_database})

    # Drop all tables
    Base.metadata.drop_all(bind=engine)
print("Database tables created.")

# Create the tables in the database.
Base.metadata.create_all(bind=engine)

# Create test users
db = SessionLocal()
user = db_models.User(
    username="test",
    password_hash=get_password_hash("test"),
    role=UserRole.ANALYST,
    privilages=[UserPrivileges.EDIT_USERS, UserPrivileges.CREATE_PROBLEMS],
    user_group="",
)
db.add(user)
db.commit()
db.refresh(user)

"""
dmUser = db_models.User(
    username="dm",
    password_hash=get_password_hash("test"),
    role=UserRole.DM,
    privilages=[],
    user_group="",
)
db.add(dmUser)

dmUser2 = db_models.User(
    username="dm2",
    password_hash=get_password_hash("test"),
    role=UserRole.DM,
    privilages=[],
    user_group="",
)
db.add(dmUser2)
"""

problem = binh_and_korn()

problem_in_db = db_models.Problem(
    owner=user.id,
    name="Binh and Korn",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.GUEST],
)
db.add(problem_in_db)

problem = nimbus_test_problem()
problem_in_db = db_models.Problem(
    owner=user.id,
    name="Test 4",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.GUEST],
)

db.add(problem_in_db)

problem = river_pollution_problem()

problem_in_db = db_models.Problem(
    name="Test 2",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.DM],
)
db.add(problem_in_db)

problem = river_pollution_problem_discrete()
problem_in_db = db_models.Problem(
    name=problem.name,
    kind=ProblemKind.DISCRETE,
    obj_kind=ObjectiveKind.DATABASED,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.DM],
)
db.add(problem_in_db)
db.commit()

problem = spanish_sustainability_problem()
problem_in_db = db_models.Problem(
    name=problem.name,
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.DM],
)
db.add(problem_in_db)
db.commit()

problem = spanish_sustainability_problem_discrete()
problem_in_db = db_models.Problem(
    name=problem.name,
    kind=ProblemKind.DISCRETE,
    obj_kind=ObjectiveKind.DATABASED,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.DM],
)
db.add(problem_in_db)
db.commit()


problem, schedule_dict = utopia_problem_old(holding=4)
problem_in_db = db_models.Problem(
    name="Test 5",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    solver=Solvers.GUROBIPY,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.DM],
)
db.add(problem_in_db)
db.commit()

# CAUTION: DO NOT PUT ANY CODE IN BETWEEN THE PREVIOUS AND FOLLOWING BLOCKS OF CODE.
# UTOPIA MAPS WILL BREAK IF YOU DO.

# The info about the map and decision alternatives now goes into the database
with open("desdeo/utopia_stuff/data/4.json") as f:  # noqa: PTH123
    forest_map = f.read()
map_info = db_models.Utopia(
    problem=problem_in_db.id,
    map_json=forest_map,
    schedule_dict=schedule_dict,
    years=["2025", "2030", "2035"],
    stand_id_field="standnumbe",
)
db.add(map_info)

problem = forest_problem_discrete()
problem_in_db = db_models.Problem(
    name=problem.name,
    kind=ProblemKind.DISCRETE,
    obj_kind=ObjectiveKind.DATABASED,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.DM],
)
db.add(problem_in_db)
db.commit()

# I guess we need to have methods in the database as well
nimbus = db_models.Method(
    kind=Methods.NIMBUS,
    properties=[],
    name="NIMBUS",
)
db.add(nimbus)
db.commit()

root_folder = "datasets/problemModels/"
# Load all json files within the root folder
problems = list(walk(root_folder))[0][2]
problems = [f for f in problems if f.endswith(".json")]

for problem in problems:  # TODO (@light-weaver): get "kind" and "obj_kind" from the problem model
    with open(root_folder + problem, encoding="utf-8") as f:
        problem_data = json.load(f)
    problem_data = Problem.model_validate(problem_data)
    problem_in_db = db_models.Problem(
        owner=user.id,
        name=problem_data.name,
        kind=ProblemKind.DISCRETE if "discrete_representation" in problem_data else ProblemKind.CONTINUOUS,
        obj_kind=ObjectiveKind.DATABASED,
        value=problem_data.model_dump(mode="json"),
        role_permission=[UserRole.GUEST],
    )
    db.add(problem_in_db)
    db.commit()

db.close()
