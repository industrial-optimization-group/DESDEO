"""A structure for group decision making.

When preferences are sent through the websockets, they are validated.
Then, the preferences are saved into a database. When all group members have articulated their
preferences, system begins optimization. The results are then saved into the database and the system notifies all
connected users that the solutions are ready to be fetched. If a user is not connected to the server, the server will
notify the user when they connect next time.

"""

import asyncio
import logging
import sys
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from jose import ExpiredSignatureError, JWTError, jwt
from sqlmodel import Session, select

from desdeo.api import AuthConfig
from desdeo.api.db import get_session
from desdeo.api.models import (
    Group,
    User,
)
from desdeo.api.routers.gdm.gdm_base import GroupManager
from desdeo.api.routers.gdm.gdm_score_bands.gdm_score_bands_manager import GDMScoreBandsManager
from desdeo.api.routers.gdm.gnimbus.gnimbus_manager import GNIMBUSManager
from desdeo.api.routers.user_authentication import get_user

logging.basicConfig(
    stream=sys.stdout, format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdm")


class ManagerManager:
    """A singleton class to manage group managers. Spawns them and deletes them.

    TODO: Also check on manager type! If a Group has a NIMBUSManager, but for
    example a RPMManager is requested, create it.
    """

    def __init__(self):
        """Class constructor."""
        # self.group_managers: dict[int, GroupManager] = {}
        self.group_managers: dict[int, dict[str, GroupManager]] = {}
        self.lock = asyncio.Lock()

    async def get_group_manager(
        self, group_id: int, method: str, db_session: Session
    ) -> GroupManager | GNIMBUSManager | GDMScoreBandsManager | None:
        """Return the correct group manager for the caller.

        Args:
            group_id (int): The ID of the group of the mgr
            method (str): The method of the group mgr
            db_session (Session): the database session passed to the manager.

        Returns:
            GroupManager | GNIMBUSManager | GDMScoreBandsManager | None: The manager (or not if not implemented.)
        """
        async with self.lock:
            if group_id in self.group_managers:
                managers = self.group_managers[group_id]
                if method in managers:
                    return managers[method]
                # If there is no manager, create it.
                match method:
                    case "gnimbus":
                        manager = GNIMBUSManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager
                    case "gdm-score-bands":
                        manager = GDMScoreBandsManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager
            else:
                self.group_managers[group_id] = {}
                match method:
                    case "gnimbus":
                        manager = GNIMBUSManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager
                    case "gdm-score-bands":
                        manager = GDMScoreBandsManager(group_id=group_id, db_session=db_session)
                        self.group_managers[group_id][method] = manager
                        return manager

    async def check_disconnect(self, group_id: int, method: str):
        """Checks if a group manager has active connections. If no, delete it.

        Args:
            group_id (int): ID of the group
            method (str): method of the manager

        Returns:
            Nothing.
        """
        async with self.lock:
            # check if group has any managers
            if group_id in self.group_managers:
                managers = self.group_managers[group_id]
                # Check if method has a manager
                if method in managers:
                    manager = managers[method]
                    # check if the manager has any active websockets
                    for _, socket in manager.sockets.items():
                        if socket is not None:
                            return
                    # No active sockets, delete the manager.
                    async with manager.lock:
                        del self.group_managers[group_id][method]
                        # If group has no managers, delete the group entry.
                        if self.group_managers[group_id] == {}:
                            del self.group_managers[group_id]


manager = ManagerManager()


async def auth_user(token: str, session: Session, websocket: WebSocket) -> User:
    """Authenticate the user.

    token: str: the access token of the user.
    session: Session: the database session from where the user is received
    websocket: WebSocket: the websocket that the user has connected with

    """

    async def error_and_close():
        await websocket.send_text("Could not validate credencials. Try logging in again.")
        await websocket.close()

    try:
        payload = jwt.decode(token, AuthConfig.authjwt_secret_key, algorithms=[AuthConfig.authjwt_algorithm])
        username = payload.get("sub")
        expire_time: datetime = payload.get("exp")

        if username is None or expire_time is None or expire_time < datetime.now(UTC).timestamp():
            return await error_and_close()

    except ExpiredSignatureError:
        return await error_and_close()

    except JWTError:
        return await error_and_close()

    user = get_user(session, username=username)

    if user is None:
        return await error_and_close()

    return user


@router.websocket("/ws")
async def websocket_endpoint(
    session: Annotated[Session, Depends(get_session)],
    websocket: WebSocket,
    token: str = Query(),
    group_id: int = Query(),
    method: str = Query(),
):
    """The websocket endpoint to which the user connects.

    Both the access token and the group id is given as a query parameter to the endpoint.
    The call to this endpoint looks like the following:

    ws://[DOMAIN]:[PORT]/gdm/ws?token=[TOKEN]&group_id=[GROUP_ID]&method=[METHOD]

    See further details in the documentation. (Explanations -> GDM and websockets)
    """
    # Accept the websocket (to send back stuff if something goes wrong)
    await websocket.accept()

    user = await auth_user(token, session, websocket)
    if user is None:
        return

    group = session.exec(select(Group).where(Group.id == group_id)).first()
    if group is None:
        await websocket.send_text(f"There is no group with ID {group_id}.")
        await websocket.close()
        return

    if not (user.id in group.user_ids or user.id is group.owner_id):
        await websocket.send_text(f"User {user.username} doesn't belong in group {group.name}")
        await websocket.close()
        return

    # We don't need the session here any more, so we can just close it.
    # I believe this releases connections to the pool
    session.close()

    # Get the group manager object from the manager of group managers
    group_manager = await manager.get_group_manager(group_id=group_id, method=method)
    if group_manager is None:
        await websocket.send_text(f"Unknown method: {method}")
        await websocket.close()
        return

    await group_manager.connect(user.id, websocket)
    logger.info(f"Group ID {group_id} manager's active connections {group_manager.sockets}")
    logger.info(f"Existing GroupManagers: {manager.group_managers}")
    while True:
        try:
            # Get data from socket
            data = await websocket.receive_text()
            # send data for preference setting
            if user.id in group.user_ids:
                await group_manager.run_method(user.id, data)
            else:
                logger.warning(
                    f"User {user.username} is not part of group {group.name}! They're likely the group owner."
                )
        except WebSocketDisconnect:
            await group_manager.disconnect(user.id, websocket)
            await manager.check_disconnect(group_id=group_id, method=method)
            logger.info(f"Group ID {group_id} manager's active connections {group_manager.sockets}")
            logger.info(f"Existing GroupManagers: {manager.group_managers}")
            break
        except RuntimeError as e:
            logger.warning(f"RuntimeError: {e}")
            break
