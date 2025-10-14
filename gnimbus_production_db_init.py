"""This module initializes the gnimbus database."""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

import requests
from sqlalchemy_utils import database_exists
from sqlmodel import Session, SQLModel, create_engine

from desdeo.api.db import engine
from desdeo.api.models import GroupCreateRequest, GroupModifyRequest, ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.problem.testproblems import dtlz2

problem = dtlz2(10, 3) # switch this out for what's needed
group_name: str = "group"


def login(username, password, server) -> str:
    """Login, returns the access token."""
    response_login = requests.post(
        f"{server}/login",
        data={"username": username, "password": password, "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=10,
    ).json()

    return response_login["access_token"]


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        dest="host",
        help="WebAPI address. E.g. localhost:8000, xyz.2.rahtiapp.fi",
        type=str
    )
    parser.add_argument(
        "-n",
        dest="uname",
        help="Group owner username",
        type=str
    )
    parser.add_argument(
        "-p",
        dest="passw",
        help="Group owner password",
        type=str
    )
    parser.add_argument(
        "-f",
        dest="filename",
        help="Path to file containing group members and their passwords",
        type=str
    )
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])

    host_prefix = args.host
    group_owner_uname = args.uname
    group_owner_pword = args.passw
    filename = args.filename

    # Have these environment variables!
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

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
            username=group_owner_uname,
            password_hash=get_password_hash(group_owner_pword),
            role=UserRole.analyst,
            group=""
        )
        session.add(user_analyst)
        session.commit()
        session.refresh(user_analyst)

        problem_db = ProblemDB.from_problem(problem, user_analyst)

        session.add(problem_db)
        session.commit()
        session.refresh(problem_db)

    group_owner_access_token = login(group_owner_uname, group_owner_pword, host_prefix)

    response = requests.post(
        url=f"{host_prefix}/gdm/create_group",
        json=GroupCreateRequest(group_name=group_name, problem_id=problem_db.id).model_dump(),
        headers={"Authorization": f"Bearer {group_owner_access_token}", "content-type": "application/json"},
        timeout=10,
    )

    with Path.open(filename) as file:
        user_content = json.load(file)

    user_list = []
    for user, password in user_content.items():
        user_list.append((user, password))

    for i, user_item in enumerate(user_list):
        uname = user_item[0]
        passw = user_item[1]
        requests.post(
            url=f"{host_prefix}/add_new_dm",
            data={"username": uname, "password": passw, "grant_type": "password"},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=10,
        )

        requests.post(
            url=f"{host_prefix}/gdm/add_to_group",
            json=GroupModifyRequest(
                group_id=1,  # We assume of that this is the only group.
                user_id=i + 2,
            ).model_dump(),
            headers={"Authorization": f"Bearer {group_owner_access_token}", "content-type": "application/json"},
            timeout=10,
        )
