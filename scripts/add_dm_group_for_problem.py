"""This module adds a group for a problem.

The problem must already exist in the database.

Takes as an argument -f a path to a json-file that should contain the user names and passwords for the group.
For example
{
  "dm1": "pw1",
  "dm2": "pw2",
}

If the users already exist their group_ids listing is updated to only contain this newly created group. This was only
done to avoid confusion the users might experience from having to choose between multiple groups, but the behavior
could be updated to allow user belonging to more than one group without anything breaking.

The argument -g is a path to a json-file that should have the fields "owner" and "problem" representing the owner of the
problem and problem name respectively. Field "group" should have the name of the group that is added.
For example
{
  "owner": "analyst",
  "problem": "testproblem",
  "group": "testi1"
}
"""

import argparse
import json
import os
import sys
from pathlib import Path

from sqlmodel import Session, create_engine, select

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
