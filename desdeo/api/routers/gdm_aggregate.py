""" A structure for group decision making.

Currently, NIMBUS has been implemented in this system. However, swapping the NIMBUS methods for some other methods, such as
reference point method should not be exceedingly difficult. I believe that if database models (in models.gdm) are generalized enough, this same
system could be used for voting for solutions, as I believe is the case with GDM methods. Generalizing, or creating a "method" info field
could be used to generalize things also.

When preferences are sent through the websockets, they are validated. Currently the validation handles only ReferencePoints.
Then, the preferences are saved into a database. When all group members have articulated their preferences, system begins optimization.
The results are then saved into the database and the system notifies all connected users that the solutions are ready to be fetched.
If a user is not connected to the server, the server will notify the user when they connect next time.

For example, in the case of NIMBUS, the last chosen solution should exist. This could be an index into the solutions.

"""

import asyncio
from datetime import UTC, datetime

import logging
import sys
logging.basicConfig(
    stream=sys.stdout,
    format='[%(filename)s:%(lineno)d] %(levelname)s: %(message)s',
    level=logging.INFO
)

from fastapi import (
    APIRouter, 
    WebSocket, 
    WebSocketDisconnect, 
    Depends,
    Query
)

from jose import JWTError, jwt, ExpiredSignatureError
from sqlmodel import Session, select
from typing import Annotated

from desdeo.api.models import (
    User, 
    Group,
)
from desdeo.api.db import get_session
from desdeo.api import SettingsConfig
from desdeo.api.routers.user_authentication import get_user
from desdeo.api.routers.gdm_base import GroupManager, ManagerException
from desdeo.api.routers.gnimbus import GNIMBUSManager


# AuthConfig
if SettingsConfig.debug:
    from desdeo.api import AuthDebugConfig

    AuthConfig = AuthDebugConfig
else:
    pass

router = APIRouter(prefix="/gdm")

class ManagerManager:
    """A singleton class to manage group managers. Spawns them and deletes them.
    TODO: Also check on manager type! If a Group has a NIMBUSManager, but for
    example a RPMManager is requested, create it.
    """

    def __init__(self):
        self.group_managers: dict[int, GroupManager] = {}
        self.lock = asyncio.Lock()


    async def get_group_manager(self, group_id: int, method: str) -> GroupManager | GNIMBUSManager:
        """Get the group manager for a specific group. If it doesn't exist, create one."""
        match method:
            case "gnimbus":    
                async with self.lock:   
                    try:
                        return self.group_managers[group_id]
                    except KeyError:
                        try:
                            group_manager = GNIMBUSManager(group_id=group_id)
                            self.group_managers[group_id] = group_manager
                            return group_manager
                        except ManagerException as e:
                            logging.warning(f"ManagerException: {e}")
                            return None
            case _:
                return None

        
    async def check_disconnect(self, group_id: int):
        """If no active connections, remove group manager"""
        async with self.lock:
            group_manager = self.group_managers[group_id]
            for _, socket in group_manager.sockets.items():
                # There are active sockets in here!
                if socket != None:
                    return
            # No active sockets, proceed with the deletion
            async with group_manager.lock:
                try:
                    del self.group_managers[group_id]
                except:
                    logging.warning(f"GroupManager for group {group_id} already deleted!")


manager = ManagerManager()

async def auth_user(
    token: str,
    session: Session,
    websocket: WebSocket
) -> User:
    """Authenticate the user

    token: str: the access token of the user.
    session: Session: the database session from where the user is received
    websocket: WebSocket: the websocket that the user has connected with
    
    """

    async def error_and_close():
        await websocket.send_text("Could not validate credencials. Try logging in again.")
        await websocket.close()
        return None

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
    method: str = Query()
):
    """ The websocket to which the user connects.

    Both the access token and the group id is given as a query parameter to the endpoint.
    The call to this endpoint looks like the following:

    ws://[DOMAIN]:[PORT]/gdm/ws?token=[TOKEN]&group_id=[GROUP_ID]&method=[METHOD]

    See further details in the documentation. (Explanations -> GDM and websockets)

    """

    # Accept the websocket (to send back stuff if something goes wrong)
    await websocket.accept()

    user = await auth_user(token, session, websocket)
    if user == None:
        return

    group = session.exec(select(Group).where(Group.id == group_id)).first()
    if group == None:
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
    if group_manager == None:
        await websocket.send_text(f"Unknown method: {method}")
        await websocket.close()
        return

    await group_manager.connect(user.id, websocket)
    logging.info(f"Group ID {group_id} manager's active connections {group_manager.sockets}")
    logging.info(f"Existing GroupManagers: {manager.group_managers}")
    while True:
        try:
            # Get data from socket
            data = await websocket.receive_text()
            # send data for preference setting
            await group_manager.run_method(user.id, data)
        except WebSocketDisconnect:
            await group_manager.disconnect(user.id, websocket)
            await manager.check_disconnect(group_id=group_id)
            logging.info(f"Group ID {group_id} manager's active connections {group_manager.sockets}")
            logging.info(f"Existing GroupManagers: {manager.group_managers}")
            break
        except RuntimeError as e:
            logging.warning(f"RuntimeError: {e}")
            break