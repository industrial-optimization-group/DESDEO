"""This module initializes the database."""

import warnings

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerDebugConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import User, UserRole, TensorConstantDB
from desdeo.problem import TensorConstant
from desdeo.api.routers.user_authentication import get_password_hash

if __name__ == "__main__":
    if SettingsConfig.debug:
        # debug stuff

        print("Creating database tables.")
        if not database_exists(engine.url):
            SQLModel.metadata.create_all(engine)
        else:
            warnings.warn("Database already exists. Clearing it.", stacklevel=1)
            # Drop all tables
            SQLModel.metadata.drop_all(bind=engine)
            SQLModel.metadata.create_all(engine)
        print("Database tables created.")

        with Session(engine) as session:
            user_analyst = User(
                username=ServerDebugConfig.test_user_analyst_name,
                password_hash=get_password_hash(ServerDebugConfig.test_user_analyst_password),
                role=UserRole.analyst,
                group="test",
            )
            session.add(user_analyst)
            session.commit()
            session.refresh(user_analyst)

            t_constant = TensorConstantDB(
                owner=user_analyst.id, name="tensor", shape=[2, 2], symbol="T", values=[[1, 2.0], [3.0, -4]]
            )

            TensorConstant.validate(t_constant.model_dump())

            session.add(t_constant)
            session.commit()
            session.refresh(t_constant)

        """
        db.add(user_analyst)
        db.commit()
        db.refresh(user_analyst)

        # add first test DM user
        user_dm1 = db_models.User(
            username=ServerDebugConfig.test_user_dm1_name,
            password_hash=get_password_hash(ServerDebugConfig.test_user_dm1_password),
            role=UserRole.DM,
            privileges=[],
            user_group="",
        )
        db.add(user_dm1)
        db.commit()
        db.refresh(user_dm1)

        # add second test DM user
        user_dm2 = db_models.User(
            username=ServerDebugConfig.test_user_dm2_name,
            password_hash=get_password_hash(ServerDebugConfig.test_user_dm2_password),
            role=UserRole.DM,
            privileges=[],
            user_group="",
        )
        db.add(user_dm2)
        db.commit()
        db.refresh(user_dm2)

        db.close()
        """

<<<<<<< HEAD
    else:
        # deployment stuff
        pass
=======
problem = river_pollution_problem()

problem_in_db = db_models.Problem(
    owner=user.id,
    name="Test 2",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    value=problem.model_dump(mode="json"),
    # role_permission=[UserRole.DM],
)
db.add(problem_in_db)

problem = river_pollution_problem_discrete()
problem_in_db = db_models.Problem(
    owner=user.id,
    name="River Pollution Problem (Discrete)",
    kind=ProblemKind.DISCRETE,
    obj_kind=ObjectiveKind.DATABASED,
    value=problem.model_dump(mode="json"),
    role_permission=[UserRole.GUEST],
)
db.add(problem_in_db)
db.commit()

problem, schedule_dict = utopia_problem_old(holding=1)
problem_in_db = db_models.Problem(
    owner=user.id,
    name="Test 5",
    kind=ProblemKind.CONTINUOUS,
    obj_kind=ObjectiveKind.ANALYTICAL,
    solver=Solvers.GUROBIPY,
    value=problem.model_dump(mode="json"),
)
db.add(problem_in_db)
db.commit()

# CAUTION: DO NOT PUT ANY CODE IN BETWEEN THE PREVIOUS AND FOLLOWING BLOCKS OF CODE.
# UTOPIA MAPS WILL BREAK IF YOU DO.

# The info about the map and decision alternatives now goes into the database
with open("desdeo/utopia_stuff/data/1.json") as f:  # noqa: PTH123
    forest_map = f.read()
map_info = db_models.Utopia(
    problem=problem_in_db.id,
    user=user.id,
    map_json=forest_map,
    schedule_dict=schedule_dict,
    years=["2025", "2030", "2035"],
    stand_id_field="standnumbe",
)
db.add(map_info)

# I guess we need to have methods in the database as well
nimbus = db_models.Method(
    kind=Methods.NIMBUS,
    properties=[],
    name="NIMBUS",
)
db.add(nimbus)
db.commit()

db.close()
>>>>>>> desdeo2
