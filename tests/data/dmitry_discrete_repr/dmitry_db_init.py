import json
import os
import warnings
from pathlib import Path

import polars as pl
from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems.dmitry_forest_problem_discrete import dmitry_forest_problem_disc

problem = dmitry_forest_problem_disc()

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

            problem_db = ProblemDB.from_problem(problem, user=user_analyst)
            session.add(problem_db)
            session.commit()
            session.refresh(problem_db)

            # We need to move the newly created test.db file to desdeo/api/ so that the api can read it.
            current_path = Path(__file__)
            target_path = current_path
            while not str(target_path).endswith("/DESDEO"):
                print(target_path)
                target_path = target_path.parent
            target_path = target_path / "desdeo/api/test.db"
            # Remove old test.db
            # os.remove(target_path / "test.db")
            # Put new one in.
            os.rename(current_path.parent / "test.db", target_path)

