"""This module adds a group for a forest problem.

The forest problem must already exist in the database.
"""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

import requests
from sqlmodel import create_engine, Session, select

from desdeo.api.models import Group, ProblemDB, User, UserRole
from desdeo.api.routers.user_authentication import get_password_hash


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f", dest="filename", help="Path to file containing group members and their passwords", type=str
    )
    parser.add_argument("-g", dest="groupfilename", help="Path to file containing info about the problem", type=str)
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])

    filename = args.filename
    groupfile = args.groupfilename

    # Have these environment variables!
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    print("Starting engine")
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    with Path.open(groupfile) as file:
        groupinfo = json.load(file)

    with Path.open(filename) as file:
        user_content = json.load(file)

    print("Loaded user and group info")

    with Session(engine) as session:
        owner = session.exec(select(User).where(User.username == groupinfo["owner"])).first()

        problem_db = session.exec(
            select(ProblemDB).where(ProblemDB.name == groupinfo["problem"], ProblemDB.user_id == owner.id)
        ).first()

        group = session.exec(select(Group).where(Group.name == groupinfo["group"])).first()
        if group is None:
            group = Group(
                name=groupinfo["group"],
                owner_id=owner.id,
                user_ids=[],
                problem_id=problem_db.id,
            )

            session.add(group)
            session.commit()
            session.refresh(group)

        print("Creating users")
        user_id_list = []
        for user, password in user_content.items():
            user_dm = session.exec(select(User).where(User.username == user)).first()

            if user_dm is None:
                user_dm = User(
                    username=user,
                    password_hash=get_password_hash(password),
                    role=UserRole.dm,
                    group_ids=[group.id],
                )
            else:
                user_dm.group_ids = [group.id]

            session.add(user_dm)
            session.commit()
            session.refresh(user_dm)

            user_id_list.append(user_dm.id)

        print("Adding user ids to group")
        group.user_ids = user_id_list

        session.add(group)
        session.commit()
        session.refresh(group)

        owner.group_ids = [group.id]
        session.add(owner)
        session.commit()
        session.refresh(owner)
        print("Finished")

else:
    pass
