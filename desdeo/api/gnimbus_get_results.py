"""Get the results of GNIMBUS."""

import argparse
import json
import sys
from pathlib import Path

import requests

from desdeo.api.models.gdm.gdm_aggregate import GroupInfoRequest


def login(username, password) -> str:
    """Login, returns the access token."""
    response_login = requests.post(
        f"{host_prefix}/login",
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
        "-g",
        dest="group",
        help="GroupID",
        type=int
    )
    parser.add_argument(
        "-u",
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
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])

    host_prefix = args.host
    group_id = args.group
    group_owner_uname = args.uname
    group_owner_pword = args.passw

    group_owner_access_token = login(group_owner_uname, group_owner_pword)

    response = requests.post(
        url=f"{host_prefix}/gnimbus/all_iterations",
        json=GroupInfoRequest(
            group_id=group_id
        ).model_dump(),
        headers={
            "Authorization": f"Bearer {group_owner_access_token}",
            "content-type": "application/json"
        },
        timeout=10,
    )

    jsoned = json.loads(response.content)

    with Path.open("all_iterations.json", "w") as file:
        json.dump(jsoned, file)
