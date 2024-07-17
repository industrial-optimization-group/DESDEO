"""This module initializes the database."""

import warnings

import numpy as np
import polars as pl
from sqlalchemy_utils import create_database, database_exists, drop_database

from desdeo.api import db_models
from desdeo.api.db import SessionLocal, engine
from desdeo.api.routers.UserAuth import get_password_hash
from desdeo.api.schema import ObjectiveKind, ProblemKind, UserPrivileges, UserRole
from desdeo.problem.schema import DiscreteRepresentation, Objective, Problem, Variable
from desdeo.problem.testproblems import binh_and_korn, nimbus_test_problem

TEST_USER = "test"
TEST_PASSWORD = "test"  # NOQA: S105 # TODO: Remove this line and create a proper user creation system.

# The following line creates the database and tables. This is not ideal, but it is simple for now.
# It recreates the tables every time the server starts. Any data saved in the database will be lost.
# TODO: Remove this line and create a proper database migration system.
print("Creating database tables.")
if not database_exists(engine.url):
    create_database(engine.url)
else:
    warnings.warn("Database already exists. Dropping and recreating it.", stacklevel=1)
    drop_database(engine.url)
    create_database(engine.url)
print("Database tables created.")

# Create the tables in the database.
db_models.Base.metadata.create_all(bind=engine)

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
problem = binh_and_korn()

problem_in_db = db_models.Problem(
    owner=user.id,
    name="Binh and Korn",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    value=problem.model_dump(mode="json"),
)
db.add(problem_in_db)

problem = nimbus_test_problem()
problem_in_db = db_models.Problem(
    owner=user.id,
    name="Test 4",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    value=problem.model_dump(mode="json"),
    role_permission=[],
)

db.add(problem_in_db)

db.commit()


# db.close()


def fakeProblemDontLook():
    # Data loading
    data = pl.read_csv("./experiment/LUKE best front.csv")
    data = data.drop(["non_dominated", "source"])
    data = data * -1
    data = data.with_columns(pl.Series("index", np.arange(1, len(data) + 1)))

    divisor_NPV = 1_000_000
    divisor_SV30 = 1_000_000
    divisor_removal = 10_000_000

    # Problem definition

    index_var = Variable(
        name="index",
        symbol="index",
        initial_value=1,
        lowerbound=1,
        upperbound=len(data),
        variable_type="real",
    )

    npv = Objective(
        name="Net present value",
        symbol="NPV",
        unit="Million EUR",
        func=None,
        objective_type="data_based",
        maximize=True,
        ideal=data["npv4%"].max() / divisor_NPV,
        nadir=data["npv4%"].min() / divisor_NPV,
    )

    sv30 = Objective(
        name="Change in standing volume",
        symbol="SV30",
        unit="Million cubic meters",
        func=None,
        objective_type="data_based",
        maximize=True,
        ideal=data["SV30"].max() / divisor_SV30,
        nadir=data["SV30"].min() / divisor_SV30,
    )

    removal1 = Objective(
        name="Yearly removal during first period",
        symbol="Removal1",
        unit="Million cubic meters",
        func=None,
        objective_type="data_based",
        maximize=True,
        ideal=data["removal1"].max() / divisor_removal,
        nadir=data["removal1"].min() / divisor_removal,
    )

    removal2 = Objective(
        name="Yearly removal during second period",
        symbol="Removal2",
        unit="Million cubic meters",
        func=None,
        objective_type="data_based",
        maximize=True,
        ideal=data["removal2"].max() / divisor_removal,
        nadir=data["removal2"].min() / divisor_removal,
    )

    removal3 = Objective(
        name="Yearly removal during third period",
        symbol="Removal3",
        unit="Million cubic meters",
        func=None,
        objective_type="data_based",
        maximize=True,
        ideal=data["removal3"].max() / divisor_removal,
        nadir=data["removal3"].min() / divisor_removal,
    )

    obj_data = {
        "NPV": ((data["npv4%"]) / divisor_NPV).to_list(),
        "SV30": ((data["SV30"]) / divisor_SV30).to_list(),
        "Removal1": ((data["removal1"]) / divisor_removal).to_list(),
        "Removal2": ((data["removal2"]) / divisor_removal).to_list(),
        "Removal3": ((data["removal3"]) / divisor_removal).to_list(),
    }

    dis_def = DiscreteRepresentation(
        variable_values={"index": data["index"].to_list()},
        objective_values=obj_data,
    )
    return Problem(
        name="LUKE Problem",
        description="None yet.",
        variables=[index_var],
        objectives=[npv, sv30, removal1, removal2, removal3],
        discrete_representation=dis_def,
    )


# luke_problem = fakeProblemDontLook()

# luke_problem_in_db = db_models.Problem(
#    owner=user.id,
#    name="LUKE Problem",
#    kind=ProblemKind.DISCRETE,
#    obj_kind=ObjectiveKind.ANALYTICAL,
#    value=luke_problem.model_dump(mode="json"),
# )
# db.add(luke_problem_in_db)
db.commit()
db.close()
