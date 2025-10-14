"""This module initializes the gnimbus database."""

import warnings

import requests
from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel

from desdeo.api.config import ServerConfig, SettingsConfig
from desdeo.api.db import engine
from desdeo.api.models import GroupCreateRequest, GroupModifyRequest, ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dtlz2

# NOTE: this is meant to be only local thing so no putting big secrets here!
server_prefix = "http://localhost:8000"
# Switch this if need be
problem = dtlz2(10, 3)
# User list (uname, password)
user_list: list[(str, str)] = [
    ("dm0", "dm0"),
    ("dm1", "dm1"),
]
group_name: str = "group_1"


def login(username="analyst", password="analyst") -> str:  # noqa: S107
    """Login, returns the access token."""
    response_login = requests.post(
        f"{server_prefix}/login",
        data={"username": username, "password": password, "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=10,
    ).json()

    return response_login["access_token"]


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

        problem_db: ProblemDB = None

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

            problem_db = ProblemDB.from_problem(problem, user_analyst)

            session.add(problem_db)
            session.commit()
            session.refresh(problem_db)

        analyst_access_token = login(ServerConfig.test_user_analyst_name, ServerConfig.test_user_analyst_password)

        response = requests.post(
            url=f"{server_prefix}/gdm/create_group",
            json=GroupCreateRequest(group_name=group_name, problem_id=problem_db.id).model_dump(),
            headers={"Authorization": f"Bearer {analyst_access_token}", "content-type": "application/json"},
            timeout=10,
        )

        for i, user_item in enumerate(user_list):
            uname = user_item[0]
            passw = user_item[1]
            requests.post(
                url=f"{server_prefix}/add_new_dm",
                data={"username": uname, "password": passw, "grant_type": "password"},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=10,
            )

            requests.post(
                url=f"{server_prefix}/gdm/add_to_group",
                json=GroupModifyRequest(
                    group_id=1,  # We assume of that this is the only group.
                    user_id=i + 2,
                ).model_dump(),
                headers={"Authorization": f"Bearer {analyst_access_token}", "content-type": "application/json"},
                timeout=10,
            )

    else:
        # deployment stuff
        pass
