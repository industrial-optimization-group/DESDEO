"""A structure for group decision making.

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
import logging
import sys

logging.basicConfig(
    stream=sys.stdout, format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)

from fastapi.responses import JSONResponse
from fastapi import HTTPException, status

from sqlmodel import Session, select
from typing import Annotated

from desdeo.api.models import (
    User,
    Group,
    GroupModifyRequest,
    GroupCreateRequest,
    GroupIteration,
    GroupInfoRequest,
    GroupPublic,
    ProblemDB,
)
from desdeo.api.db import get_session
from desdeo.api import AuthConfig
from desdeo.api.routers.user_authentication import get_current_user

router = APIRouter(prefix="/gdm")


class ManagerException(Exception):
    """If something goes awry with the manager"""


class GroupManager:
    """A group manager. Manages connections, disconnections, optimization and communication to users."""

    def __init__(self, group_id: int):
        """Initializes the instance of the group manager."""
        self.lock = asyncio.Lock()
        self.sockets: dict[int, WebSocket] = {}
        self.group_id: int = group_id

        # Get session and make sure the group exists
        session = next(get_session())
        group = session.exec(select(Group).where(Group.id == group_id)).first()
        if group == None:
            session.close()
            raise ManagerException(f"No group with ID {group_id} found!")

        # Initialize the socket dict (at the very least to avoid KeyErrors)
        for user_id in group.user_ids:
            self.sockets[user_id] = None

        session.close()

    async def send_message(self, message: str, websocket: WebSocket):
        """Notify the user of the existing results that have to be fetched"""
        try:
            await websocket.send_text(message)
        except WebSocketDisconnect:
            return

    async def connect(self, user_id: int, websocket: WebSocket):
        """Connect to websocket

        The connection has been accepted beforehand for sending error messages
        back to user, but here we attach it to the manager instance.
        """

        self.sockets[user_id] = websocket

        # If there are pending notifications, send notifications
        session = next(get_session())
        group = session.exec(select(Group).where(Group.id == self.group_id)).first()
        try:
            prev_iter = group.head_iteration.parent
            if prev_iter == None:
                session.close()
                return
            if not prev_iter.notified[str(user_id)]:
                await self.send_message("Please fetch results.", websocket)
                notified = prev_iter.notified.copy()
                notified[user_id] = True
                prev_iter.notified = notified
                session.add(prev_iter)
                session.commit()
                session.close()
        except:
            session.close()
            return

    async def disconnect(self, user_id: int, websocket: WebSocket):
        """Disconnect from websocket

        The connection has been closed beforehand, but here we detach the WebSocket
        object from the manager instance.
        """
        if self.sockets[user_id] == websocket:
            self.sockets[user_id] = None

    async def broadcast(self, message: str):
        """Send message to all connected websockets"""
        for _, socket in self.sockets.items():
            if socket != None:
                try:
                    await socket.send_text(message)
                except WebSocketDisconnect:
                    continue

    async def notify(
        self,
        user_ids: list[int],
        message: str,
    ) -> dict[int, bool]:
        notified = {}
        for user_id in user_ids:
            try:
                socket: WebSocket = self.sockets[user_id]
                if socket != None:
                    await self.send_message(message, socket)
                    notified[user_id] = True
                else:
                    notified[user_id] = False
            except KeyError:
                notified[user_id] = False
        return notified

    async def run_method(
        self,
        user_id: int,
        data: str,
    ):
        """The function to run the method

        One could derive different managers from this GroupManager
        class and implement method and manager-specific "run_method" functions.

        """


@router.post("/create_group")
def create_group(
    request: GroupCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Create group.

    Args:
        request (GroupCreateRequest): a request that holds information to be used in creation of the group.
        user (Annotated[User, Depends(get_current_user)]): the current user.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: Aknowledgement that the gourp was created

    Raises:
        HTTPException
    """

    problem = session.exec(select(ProblemDB).where(ProblemDB.id == request.problem_id)).first()
    if problem == None:
        raise HTTPException(
            detail=f"There's no problem with ID {request.problem_id}!", status_code=status.HTTP_404_NOT_FOUND
        )

    group = Group(owner_id=user.id, user_ids=[], problem_id=request.problem_id, name=request.group_name)

    session.add(group)
    session.commit()
    session.refresh(group)

    group_ids = user.group_ids.copy()
    group_ids.append(group.id)
    user.group_ids = group_ids

    session.add(user)
    session.commit()

    return JSONResponse(content={"message": f"Group with ID {group.id} created."}, status_code=status.HTTP_201_CREATED)


@router.post("/delete_group")
def delete_group(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Delete the group with given ID

    Args:
        request (GroupInfoRequest): Contains the ID of the group to be deleted
        user (Annotated[User, Depends(get_current_user)]): The user (in this case must be owner for anything to happen)
        session (Annotated[Session, Depends(get_session)]): The database session

    Returns:
        JSONResponse: Aknowledgement of the deletion

    Raises:
        HTTPException: Insufficient authorization etc.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group == None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found.", status_code=status.HTTP_404_NOT_FOUND)

    if user.id != group.owner_id:
        raise HTTPException(
            detail="Only the owner of a group may delete the group.", status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Remove the group from users
    user_ids = group.user_ids
    for id in user_ids:
        group_user = session.exec(select(User).where(User.id == id)).first()
        ugids = group_user.group_ids.copy()
        ugids.remove(group.id)
        group_user.group_ids = ugids
        session.add(group_user)
        session.commit()

    ugids = user.group_ids.copy()
    ugids.remove(group.id)
    user.group_ids = ugids
    session.add(user)
    session.commit()
    session.refresh(user)

    # Get the root iteration
    head: GroupIteration = group.head_iteration
    iter_count = 0
    if head != None:
        while head.parent != None:
            head = head.parent
            iter_count += 1

        # First delete the corresponding group iterations
        # This deletes the rest of the iterations due to cascades
        session.delete(head)
        session.commit()

    # Then delete the group
    session.delete(group)
    session.commit()

    # Make sure that the group IS deleted!
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group != None:
        raise HTTPException(
            detail="Couldn't delete group from the database!", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return JSONResponse(
        content={"message": f"Group with ID {request.group_id} and its {iter_count} iterations have been deleted."},
        status_code=status.HTTP_200_OK,
    )


@router.post("/add_to_group")
def add_to_group(
    request: GroupModifyRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Add a user to a group.

    Args:
        request (GroupModifyRequest): Request object that has group and user IDs.
        user (Annotated[User, Depends(get_current_user)]): the current user.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: Aknowledge that user has been added to the group

    Raises:
        HTTPException: Authorization issues, group or user not found.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    # Make sure the group exists
    if group == None:
        raise HTTPException(
            detail=f"There's no group with ID {request.group_id}", status_code=status.HTTP_404_NOT_FOUND
        )
    # Make sure of proper authorization
    if not group.owner_id == user.id:
        raise HTTPException(detail="Unauthorized user", status_code=status.HTTP_401_UNAUTHORIZED)

    if request.user_id in group.user_ids:
        raise HTTPException(
            detail=f"User with ID {request.user_id} already in this group!", status_code=status.HTTP_400_BAD_REQUEST
        )

    addee = session.exec(select(User).where(User.id == request.user_id)).first()
    # Make sure the user to be added exists
    if addee == None:
        raise HTTPException(
            detail=f"There is no user with ID {request.user_id}!", status_code=status.HTTP_404_NOT_FOUND
        )

    users = group.user_ids.copy()
    users.append(request.user_id)
    group.user_ids = users
    session.add(group)
    session.commit()
    session.refresh(group)

    if addee.group_ids == None:
        addee.group_ids = [group.id]
    else:
        groups = addee.group_ids.copy()
        groups.append(group.id)
        addee.group_ids = groups

    session.add(addee)
    session.commit()
    session.refresh(addee)

    return JSONResponse(
        content={"message": f"Added user {group.user_ids[-1]} to group {group.id}."}, status_code=status.HTTP_200_OK
    )


@router.post("/remove_from_group")
def remove_from_group(
    request: GroupModifyRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """Remove user from group.

    Args:
        request (GroupModifyRequest): Request object that has group and user IDs.
        user (Annotated[User, Depends(get_current_user)]): the current user.
        session (Annotated[Session, Depends(get_session)]): the database session.

    Returns:
        JSONResponse: Aknowledge that user has been removed from the group.

    Raises:
        HTTPException: Authorization issues, group or user not found.
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    # Make sure the group exists
    if group == None:
        raise HTTPException(detail=f"No group with ID {request.group_id} found.", status_code=status.HTTP_404_NOT_FOUND)
    # Make sure of proper authorization
    authorized = user.id == group.owner_id or user.id == request.user_id

    if not authorized:
        raise HTTPException(detail="Unauthorized user", status_code=status.HTTP_401_UNAUTHORIZED)

    if request.user_id not in group.user_ids:
        raise HTTPException(
            detail=f"User with ID {request.user_id} is not in this group!", status_code=status.HTTP_400_BAD_REQUEST
        )

    user_ids = group.user_ids.copy()
    user_ids.remove(request.user_id)
    group.user_ids = user_ids
    session.add(group)
    session.commit()
    session.refresh(group)

    removed_user = session.exec(select(User).where(User.id == request.user_id)).first()
    ugids = removed_user.group_ids.copy()
    ugids.remove(group.id)
    removed_user.group_ids = ugids
    session.add(removed_user)
    session.commit()

    if request.user_id in group.user_ids:
        raise HTTPException(
            detail=f"Could not remove User {request.user_id} from group {request.group_id}.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content={"message": f"User {request.user_id} removed from group {request.group_id}."},
        status_code=status.HTTP_200_OK,
    )


@router.post("/get_group_info")
def get_group_info(
    request: GroupInfoRequest,
    session: Annotated[Session, Depends(get_session)],
) -> GroupPublic:
    """Get information about the group

    Args:
        request (GroupInfoRequest): the id of the group for which we desire info on
        session (Annotated[Session, Depends(get_session)]): the database session

    Returns:
        GroupPublic: public info of the group

    Raises:
        HTTPException: If there's no group with the requests group id
    """
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group == None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return group
