"""This module initializes the database."""

import warnings
import json

from pathlib import Path

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerDebugConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole, ProblemMetaDataDB, ForestProblemMetaData
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dtlz2, river_pollution_problem, simple_knapsack
from desdeo.problem import Problem

def _generate_descriptions(mapjson: dict, sid: str, stand: str, holding: str, extension: str) -> dict:
    descriptions = {}
    if holding:
        for feat in mapjson["features"]:
            if False:  # noqa: SIM108
                ext = f".{feat["properties"][extension]}"
            else:
                ext = ""
            descriptions[feat["properties"][sid]] = (
                f"Ala {feat["properties"][holding].split("-")[-1]} kuvio {feat["properties"][stand]}{ext}: "
            )
    else:
        for feat in mapjson["features"]:
            if False:  # noqa: SIM108
                ext = f".{feat["properties"][extension]}"
            else:
                ext = ""
            descriptions[feat["properties"][sid]
                         ] = f"Kuvio {feat["properties"][stand]}{ext}: "
    return descriptions

problems = [dtlz2(10, 3), simple_knapsack(), river_pollution_problem()]

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

            for problem in problems:
                problem_db = ProblemDB.from_problem(problem, user_analyst)

                session.add(problem_db)

            session.commit()
            session.refresh(problem_db)

            # UTOPIA specific stuff
            with Path("/home/vili/output/utopia_test/problem.json").open(mode="r") as file:
                problem = file.read()
            problem = Problem.model_validate_json(problem, by_name=True)

            problem_db = ProblemDB.from_problem(problem, user=user_analyst)
            session.add(problem_db)
            session.commit()
            session.refresh(problem_db)
            
            with Path("/home/vili/output/utopia_test/key.json").open(mode="r") as file:
                schedule_dict = json.load(file)
            
            with Path("/home/vili/output/utopia_test/utopia_test.geojson").open(mode="r") as file:
                map_json = file.read()
            
            utopia_metadata = ForestProblemMetaData(
                map_json=map_json,
                schedule_dict=schedule_dict,
                years=["5", "10", "20"],
                stand_id_field="id",
                stand_descriptor=_generate_descriptions(
                    json.loads(map_json),
                    "id",
                    "number",
                    "estate_code",
                    "extension"
                ),
                compensation=None
            )

            problem_metadata_db = ProblemMetaDataDB(
                problem_id=problem_db.id,
                data=[utopia_metadata]
            )
            session.add(problem_metadata_db)
            session.commit()
            session.refresh(problem_metadata_db)


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

    else:
        # deployment stuff
        pass
