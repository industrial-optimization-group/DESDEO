"""Get the results of GNIMBUS."""

import json
from pathlib import Path

import requests

from desdeo.api.config import ServerConfig
from desdeo.api.models.gdm.gdm_aggregate import GroupInfoRequest

server_prefix = "http://localhost:8000"
group_id = 1


def login(username="analyst", password="analyst") -> str:  # noqa: S107
    """Login, returns the access token."""
    response_login = requests.post(
        f"{server_prefix}/login",
        data={"username": username, "password": password, "grant_type": "password"},
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=10,
    ).json()

    return response_login["access_token"]


analyst_access_token = login(ServerConfig.test_user_analyst_name, ServerConfig.test_user_analyst_password)

response = requests.post(
    url=f"{server_prefix}/gnimbus/all_iterations",
    json=GroupInfoRequest(
        group_id=group_id  # we assume there's only one group!
    ).model_dump(),
    headers={"Authorization": f"Bearer {analyst_access_token}", "content-type": "application/json"},
    timeout=10,
)

jsoned = json.loads(response.content)

with Path.open("all_iterations.json", "w") as file:
    json.dump(jsoned, file)
