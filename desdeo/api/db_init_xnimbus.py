"""This module initializes the database."""

import warnings

from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import (
    river_pollution_problem,
    spanish_sustainability_problem,
)

problems = [
    river_pollution_problem(five_objective_variant=False),
    spanish_sustainability_problem(),
]

if __name__ == "__main__":
    num_users = 5  # Number of random users to create for testing purposes
    user_name_prefix = "nimbus"
    analyst_usernames = ["kmiettinen", "bafsar", "glarraga"]
    password_length = 5

    # It creates a dataset with the usernames and passwords
    user_password_dataset = []

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

        # Add multiple test analyst users
        for i in range(len(analyst_usernames)):
            with Session(engine) as session:
                user_analyst = User(
                    username=analyst_usernames[i],
                    password_hash=get_password_hash(f"analyst{i+1}"),
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

                user_password_dataset.append((analyst_usernames[i], f"analyst{i+1}"))

        # Add main test analyst user
        with Session(engine) as session:
            user_analyst = User(
                username=ServerConfig.test_user_analyst_name,
                password_hash=get_password_hash(
                    ServerConfig.test_user_analyst_password
                ),
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
            user_password_dataset.append(
                (
                    ServerConfig.test_user_analyst_name,
                    ServerConfig.test_user_analyst_password,
                )
            )

        # Add randomly generated usernames and passwords for testing purposes
        for i in range(num_users):
            with Session(engine) as session:
                username = f"{user_name_prefix}_{i+1}"
                password = "".join(
                    __import__("random").choices(
                        __import__("string").ascii_letters
                        + __import__("string").digits,
                        k=password_length,
                    )
                )
                user = User(
                    username=username,
                    password_hash=get_password_hash(password),
                    role=UserRole.dm,
                    group="test",
                )
                session.add(user)
                session.commit()
                session.refresh(user)

                # Here we can decide if we want to reorder the objectives or not
                for problem in problems:
                    problem_db = ProblemDB.from_problem(problem, user)

                    session.add(problem_db)

                session.commit()
                session.refresh(problem_db)

                user_password_dataset.append((username, password))

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
        # Save the dataset to a file
        with open("user_password_dataset.csv", "w") as f:
            for username, password in user_password_dataset:
                f.write(f"{username},{password}\n")

    else:
        # deployment stuff
        pass
