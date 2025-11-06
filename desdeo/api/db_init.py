"""This module initializes the database."""

import warnings
from pathlib import Path

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import (
    ProblemDB,
    ProblemMetaDataDB,
    SolverSelectionMetadata,
    User,
    UserRole,
)
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem import Problem
from desdeo.problem.testproblems import dtlz2, river_pollution_problem, simple_knapsack

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
                username=ServerConfig.test_user_analyst_name,
                password_hash=get_password_hash(ServerConfig.test_user_analyst_password),
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

            # Add clinic problem
            problem_path = Path("/home/kilo/Downloads/clinicOptProb_ideal_and_nadir.json")

            problem = Problem.load_json(problem_path)
            problem_db = ProblemDB.from_problem(problem, user_analyst)

            session.add(problem_db)
            session.commit()
            session.refresh(problem_db)

            metadata = ProblemMetaDataDB(problem_id=problem_db.id, problem=problem_db)
            session.add(metadata)
            session.commit()
            session.refresh(metadata)

            solver_metadata = SolverSelectionMetadata(
                metadata_id=metadata.id, solver_string_representation="pyomo_ipopt", metadata_instance=metadata
            )
            session.add(solver_metadata)
            session.commit()

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
