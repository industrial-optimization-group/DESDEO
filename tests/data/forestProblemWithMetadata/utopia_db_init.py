"""This module initializes the database."""

import warnings
import os
import json

from pathlib import Path

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole, ForestProblemMetaData, ProblemMetaDataDB
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.tools.desc_gen import generate_descriptions
from desdeo.problem.schema import Problem

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
                username=ServerConfig.test_user_analyst_name,
                password_hash=get_password_hash(ServerConfig.test_user_analyst_password),
                role=UserRole.analyst,
                group="test",
            )
            session.add(user_analyst)
            session.commit()
            session.refresh(user_analyst)

            current_path = Path(__file__)
            path = current_path
            while not str(path).endswith("/DESDEO"):
                path = path.parent
            path = path / "tests/data/forestProblemWithMetadata/"

            # load the problem from json
            with Path(path / "problem.json").open(mode="r") as file:
                problem = Problem.model_validate(json.load(file), by_name=True)
            problem_db = ProblemDB.from_problem(problem, user=user_analyst)
            session.add(problem_db)
            session.commit()
            session.refresh(problem_db)

            with Path(path / "key.json").open(mode="r") as file:
                key = json.load(file)

            with Path(path / "utopia_test.geojson").open(mode="r") as file:
                map_json = file.read()

            forest_metadata = ForestProblemMetaData(
                map_json=map_json,
                schedule_dict=key,
                years=list(map(lambda x: str(x), [5, 10, 20])),
                stand_id_field="id",
                stand_descriptor=generate_descriptions(
                    json.loads(map_json), "id", "number", "estate_code", "extension"
                ),
            )

            metadata_db = ProblemMetaDataDB(
                problem_id=problem_db.id, forest_metadata=[forest_metadata], problem=problem_db
            )

            session.add(metadata_db)
            session.commit()

            # We need to move the newly created test.db file to desdeo/api/ so that the api can read it.
            target_path = current_path
            while not str(target_path).endswith("/DESDEO"):
                print(target_path)
                target_path = target_path.parent
            target_path = target_path / "desdeo/api/test.db"
            # Remove old test.db
            # os.remove(target_path / "test.db")
            # Put new one in.
            os.rename(current_path.parent / "test.db", target_path)

    else:
        # deployment stuff
        pass
