"""A very complicated mess"""

import asyncio

from fastapi import (
    APIRouter, 
    WebSocket, 
    WebSocketDisconnect, 
    Depends
)
from fastapi.responses import JSONResponse
from fastapi import HTTPException, status

from sqlmodel import Session, select
from typing import Annotated, Any

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
from desdeo.api.routers.user_authentication import get_current_user

class ManagerException(Exception):
    """If something goes awry with the manager"""

router = APIRouter(prefix="/gdm")

debug = True

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
            raise ManagerException(f"No group with ID {group_id} found!")
        
        # Make sure first iteration exists
        try:
            group.group_iterations[-1]
        except:
            raise ManagerException(f"No iterations found for group {group.name}")


    async def notify(self, websocket: WebSocket):
        """Notify the user of the existing results that have to be fetched"""
        try:
            await websocket.send_text("Please fetch results.")
        except WebSocketDisconnect:
            return


    async def connect(
        self,
        user_id: int,
        websocket: WebSocket
    ):
        """Connect to websocket"""
        await websocket.accept()
        self.sockets[user_id] = websocket

        # If there are pending notifications, send notifications
        session = next(get_session())
        group = session.exec(select(Group).where(Group.id == self.group_id)).first()
        try:
            prev_iter = group.group_iterations[-1].parent
            if prev_iter == None:
                return
            if not prev_iter.notified[str(user_id)]:
                if debug:
                    print("notifying")
                await self.notify(websocket)
                notified = prev_iter.notified.copy()
                notified[user_id] = True
                prev_iter.notified = notified
                session.add(prev_iter)
                session.commit()
        except:
            return


    async def disconnect(
        self, 
        user_id: int,
        websocket: WebSocket
    ):
        """Disconnect from websocket"""
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


    # A dummy for implementing actual optimization
    async def run_optim(self):
        """A dummy for implementing actual optimization"""
        # Synthesize preferences, details are method specific I believe
        await asyncio.sleep(1)
        session = next(get_session())
        group = session.exec(select(Group).where(Group.id == self.group_id)).first()
        prefs = group.group_iterations[-1].set_preferences
        message = ""
        for usr, pref in prefs.items():
            message = message + f"{usr} : {pref}; "
        await self.broadcast(message)

        # Optimize
        await asyncio.sleep(7)
        await self.broadcast("optimizin' done")
        print(f"Optimization for group {self.group_id} done.")

        # ADD optimization results into database


    async def set_preference(self, user_id: int, data: str):
        """Set preferences of the user"""

        # Set the lock
        async with self.lock:

            # Fetch the current iteration
            session = next(get_session())
            group = session.exec(select(Group).where(Group.id == self.group_id)).first()
            group_iterations = group.group_iterations
            current_iteration = group_iterations[-1]

            if debug:
                print(current_iteration.id)

            # Update iteration preferences
            set_prefs = current_iteration.set_preferences.copy()
            set_prefs[user_id] = data
            current_iteration.set_preferences = set_prefs
            session.add(current_iteration)
            session.commit()
            session.refresh(current_iteration)

            # Check if all preferences are in
            for user_id in group.user_ids:
                try:
                    if current_iteration.set_preferences[str(user_id)] == None:
                        if debug: print("Not all prefs in!")
                        return
                except KeyError:
                    if debug: 
                        print("Key error: Not all prefs in!")
                        print(current_iteration.set_preferences)
                    return
            
            # If all preferences are in, begin optimization.
            await self.run_optim()

            # notify connected users that the optimization is done
            notified = {}
            for user_id in group.user_ids:
                socket: WebSocket = self.sockets[user_id]
                print(socket)
                if socket != None:
                    await self.notify(socket)
                    notified[user_id] = True
                else:
                    notified[user_id] = False
            # Update iteration's notifcation database item
            current_iteration.notified = notified
            session.add(current_iteration)
            session.commit()
            session.refresh(current_iteration)
            
            # After optimization, add new iteration
            next_iteration = GroupIteration(
                group_id=self.group_id,
                group=group,
                problem_id=current_iteration.problem_id,
                set_preferences={},
                notified={},
                parent_id=current_iteration.id, # Probably redundant to have
                parent=current_iteration,       # two connections to parents?
                child=None,
            )
            session.add(next_iteration)
            session.commit()
            session.refresh(next_iteration)

            # Update database 
            current_iteration.child = next_iteration
            session.add(current_iteration)
            session.commit()
            session.refresh(current_iteration)

            new_group_iterations = group_iterations.copy()  # bruh (perhaps we should just use index list?)
            new_group_iterations.append(next_iteration)     # seems super inefficient
            group.group_iterations = new_group_iterations
            session.add(group)
            session.commit()
            session.refresh(group)

            
class ManagerManager:
    """A class to manage group managers. Spawns them and deletes them."""


    def __init__(self):
        self.group_managers: dict[int, GroupManager] = {}
        self.lock = asyncio.Lock()


    async def get_group_manager(self, group_id: int) -> GroupManager:
        """Get the group manager for a specific group. If it doesn't exist, create one."""
        async with self.lock:
            try:
                    return self.group_managers[group_id]
            except KeyError:
                group_manager = GroupManager(group_id=group_id)
                self.group_managers[group_id] = group_manager
                return group_manager

        
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
                    if debug:
                        print(f"Group {group_id} already deleted!")


manager = ManagerManager()


@router.websocket("/ws/{group_id}/{user_id}")
async def websocket_endpoint(
    group_id: str,
    user_id: str,
    session: Annotated[Session, Depends(get_session)],
    websocket: WebSocket,
):
    group_id_int = int(group_id)
    user_id_int = int(user_id)

    group = session.exec(select(Group).where(Group.id == group_id_int)).first()
    if group == None:
        raise HTTPException(
            detail=f"No group with ID {group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Validate user.
    user = session.exec(select(User).where(User.id == user_id_int)).first()
    if user == None:
        raise HTTPException(
            detail=f"User with id {user_id} not found.",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    if user.id not in group.user_ids:
        raise HTTPException(
            detail=f"User {user.username} doesn't belong in group {group.name}!",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    print(f"{user.username} has joined.")

    # Get the group manager object from the manager of group managers
    group_manager = await manager.get_group_manager(group_id=group_id_int)
    await group_manager.connect(user_id_int, websocket)
    if debug:
        print(group_manager.group_id)
        print(group_manager.sockets)
    try:
        while True:
            # Get data from socket
            data = await websocket.receive_text()
            await group_manager.broadcast(message=f"{user_id_int}: {data}")
            if data.startswith("pref: "):
                asyncio.create_task(group_manager.set_preference(user_id_int, data[6:]))
    except WebSocketDisconnect:
        await group_manager.disconnect(user_id_int, websocket)
        await group_manager.broadcast(message=f"{user_id_int} left the chat")
        if debug:
            print(group_manager.sockets)
            print(manager.group_managers)
        await manager.check_disconnect(group_id=group_id_int)

@router.post("/create_group")
def create_group(
    request: GroupCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
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
            detail=f"There's no problem with ID {request.problem_id}!",
            status_code=status.HTTP_404_NOT_FOUND
        )

    group = Group(
        owner_id=user.id,
        user_ids=[user.id],
        problem_id=request.problem_id,
        name=request.group_name
    )

    session.add(group)
    session.commit()
    session.refresh(group)

    user.group_ids = [group.id]

    session.add(user)
    session.commit()

    # Create base group iteration
    first_iteration = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        group=group,
        set_preferences={},
        notified={},
        parent_id=None,
        parent=None,
        child=None
    )

    session.add(first_iteration)
    session.commit()

    return JSONResponse(
        content={"message": f"Group with ID {group.id} created."},
        status_code=status.HTTP_201_CREATED
    )

@router.post("/add_to_group")
def add_to_group(
    request: GroupModifyRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
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
            detail="There's no such group!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    # Make sure of proper authorization 
    if not group.owner_id == user.id:
        raise HTTPException(
            detail="Unauthorized user",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    if request.user_id in group.user_ids:
        raise HTTPException(
            detail="User already in this group!",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    addee = session.exec(select(User).where(User.id == request.user_id)).first()
    # Make sure the user to be added exists
    if addee == None:
        raise HTTPException(
            detail=f"There is no user with ID {request.user_id}!",
            status_code=status.HTTP_404_NOT_FOUND
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
        content={"message": f"Added user {group.user_ids[-1]} to group {group.id}."},
        status_code=status.HTTP_200_OK
    )


@router.post("/remove_from_group")
def remove_from_group(
    request: GroupModifyRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
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
        raise HTTPException(
            detail="There's no such group!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    # Make sure of proper authorization 
    authorized = True if (user.id == group.owner_id or user.id == request.user_id) else False

    if not authorized:
        raise HTTPException(
            detail="Unauthorized user",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    if request.user_id not in group.user_ids:
        raise HTTPException(
            detail="User is not in this group!",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    user_ids = group.user_ids.copy()
    user_ids.remove(request.user_id)
    group.user_ids = user_ids
    session.add(group)
    session.commit()
    session.refresh(group)

    if request.user_id in group.user_ids:
        raise HTTPException(
            detail=f"Could not remove User {request.user_id} from group {request.group_id}.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return JSONResponse(
        content={"message": f"User {request.user_id} removed from group {request.group_id}."},
        status_code=status.HTTP_200_OK
    )

@router.post("/get_group_info")
def get_group_info(
    request: GroupInfoRequest,
    session: Annotated[Session, Depends(get_session)],
) -> GroupPublic:
    """Get information about the group"""
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group == None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    return group

@router.post("/get_results")
def get_results(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> Any:
    pass
