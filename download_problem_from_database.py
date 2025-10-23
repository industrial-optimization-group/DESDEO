"""This module adds a group for a forest problem.

The forest problem must already exist in the database.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from sqlmodel import create_engine, Session, select

from desdeo.api.models import Group, ProblemDB, User, UserRole

from desdeo.problem import Problem


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

        problem_db = session.exec(select(ProblemDB).where(ProblemDB.name == groupinfo.problem)).first()

        problem = Problem.from_problemdb(problem_db)

        problem.save_to_json(Path("utopia_forest.json"))

        print("Finished")

else:
    pass
