import os
import warnings
from sqlalchemy_utils import database_exists, create_database
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import (
    river_pollution_problem,
    spanish_sustainability_problem,
    rocket_injector_design,
)

problems = [
    river_pollution_problem(five_objective_variant=False),
    spanish_sustainability_problem(),
    rocket_injector_design(),
    rocket_injector_design(True),
]

RESET_DB = 1
SEED_DB = 1  # optional


def ensure_database_exists():
    # For Postgres/MySQL: creates the database itself if missing.
    # For SQLite: not needed, but harmless.
    if not database_exists(engine.url):
        create_database(engine.url)


def init_schema():
    print(f"Database URL: {engine.url}")

    ensure_database_exists()

    if RESET_DB:
        warnings.warn("RESET_DB=1 -> Dropping and recreating ALL tables.", stacklevel=1)
        SQLModel.metadata.drop_all(bind=engine)

    SQLModel.metadata.create_all(engine)
    print("Database tables initialized.")


def seed_data():
    # Seed only if you want it (recommended only for dev/staging)
    num_users = 10
    user_name_prefix = "nimbus"
    analyst_usernames = ["kmiettinen", "bafsar", "glarraga"]
    password_length = 5

    user_password_dataset = []

    # Add multiple test analyst users
    for i, uname in enumerate(analyst_usernames):
        with Session(engine) as session:
            user_analyst = User(
                username=uname,
                password_hash=get_password_hash(f"analyst{i+1}"),
                role=UserRole.analyst,
                group="test",
            )
            session.add(user_analyst)
            session.commit()
            session.refresh(user_analyst)

            for problem in problems:
                session.add(ProblemDB.from_problem(problem, user_analyst))

            session.commit()
            user_password_dataset.append((uname, f"analyst{i+1}"))

    # Add main test analyst user (only if ServerConfig exists)
    if ServerConfig is not None:
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
                session.add(ProblemDB.from_problem(problem, user_analyst))

            session.commit()
            user_password_dataset.append(
                (
                    ServerConfig.test_user_analyst_name,
                    ServerConfig.test_user_analyst_password,
                )
            )

    # Random users
    import random, string

    for i in range(num_users):
        with Session(engine) as session:
            username = f"{user_name_prefix}_{i+1}"
            password = "".join(
                random.choices(string.ascii_letters + string.digits, k=password_length)
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

            for problem in problems:
                session.add(ProblemDB.from_problem(problem, user))

            session.commit()
            user_password_dataset.append((username, password))

    with open("user_password_dataset.csv", "w") as f:
        for username, password in user_password_dataset:
            f.write(f"{username},{password}\n")

    print("Seed data created.")


if __name__ == "__main__":
    print("Initializing database...")
    init_schema()

    if SEED_DB:
        seed_data()

    print("Database initialization complete.")
