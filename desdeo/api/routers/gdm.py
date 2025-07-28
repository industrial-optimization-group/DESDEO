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
import json
from datetime import UTC, timedelta, datetime

from fastapi import (
    APIRouter, 
    WebSocket, 
    WebSocketDisconnect, 
    Depends,
    Query
)

from fastapi.responses import JSONResponse
from fastapi import HTTPException, status

from jose import JWTError, jwt, ExpiredSignatureError
from sqlmodel import Session, select
from pydantic import ValidationError
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
    ReferencePoint
)
from desdeo.api.db import get_session
from desdeo.api import SettingsConfig
from desdeo.api.routers.user_authentication import get_current_user, get_user
from desdeo.problem import Problem
from desdeo.mcdm.nimbus import generate_starting_point, solve_sub_problems
from desdeo.tools import SolverResults
from desdeo.tools.scalarization import ScalarizationError

# AuthConfig
if SettingsConfig.debug:
    from desdeo.api import AuthDebugConfig

    AuthConfig = AuthDebugConfig
else:
    pass

router = APIRouter(prefix="/gdm")
debug = True

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
            raise ManagerException(f"No group with ID {group_id} found!")
        
        # Make sure first iteration exists
        if group.head_iteration == None:
            raise ManagerException(f"No iterations found for group {group.name}")
        
        # Initialize the socket dict (at the very least to avoid KeyErrors)
        for user_id in group.user_ids:
            self.sockets[user_id] = None


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


    # A dummy for implementing actual optimization
    async def run_optim(self):
        """A dummy for implementing actual optimization"""
        # Synthesize preferences, details are method specific I believe
        session = next(get_session())
        group = session.exec(select(Group).where(Group.id == self.group_id)).first()
        problem_db: ProblemDB = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
        problem: Problem = Problem.from_problemdb(problem_db)
        iteration = group.head_iteration
        prefs = iteration.set_preferences
        
        # Here we choose only one preference as an example
        pref = prefs[str(group.user_ids[0])].aspiration_levels
        #NOTE: NIMBUS METHOD; Integrate states into this system
        try:
            results = solve_sub_problems(
                problem,
                reference_point=pref,
                num_desired=4,
                current_objectives=iteration.parent.results[0].optimal_objectives # just one example, figure out how to switch this
            )
            print(f"Optimization for group {self.group_id} done.")

            # ADD optimization results into database
            iteration.results = results
            session.add(iteration)
            session.commit()

            return True
        
        except ScalarizationError:
            await self.broadcast("Error while scalarizing: classifications must differ from previous iteration!")
            return False

        except Exception as e:
            await self.broadcast(f"An error occured while optimizing: {e}")
            return False
        
        return False


    async def set_preference(self, user_id: int, data: ReferencePoint):
        """Set preferences of the user"""

        # Set the lock
        async with self.lock:

            # Fetch the current iteration
            session = next(get_session())
            group = session.exec(select(Group).where(Group.id == self.group_id)).first()
            if group == None:
                await self.broadcast(f"The group with ID {self.group_id} doesn't exist anymore.")
            current_iteration = group.head_iteration

            if current_iteration.parent == None:
                await self.broadcast("Problem not initialized! Initialize the problem!")
                return

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
            success = await self.run_optim()

            # If the optimization succeeds, update the iteration
            # TODO: might want to move making new iterations to the optimization functions
            if success:
                # notify connected users that the optimization is done
                notified = {}
                for user_id in group.user_ids:
                    try:
                        socket: WebSocket = self.sockets[user_id]
                        if debug:
                            print(socket)
                        if socket != None:
                            await self.notify(socket)
                            notified[user_id] = True
                        else:
                            notified[user_id] = False
                    except KeyError:
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

                # Update head
                group.head_iteration = next_iteration
                session.add(group)
                session.commit()

            
class ManagerManager:
    """A singleton class to manage group managers. Spawns them and deletes them."""


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
    group_id: int = Query()
):
    """ The websocket to which the user connects.

    Both the access token and the group id is given as a query parameter to the endpoint.
    The call to this endpoint looks like the following:

    ws://[DOMAIN]:[PORT]/gdm/ws?token=[TOKEN]&group_id=[GROUP_ID]

    The data sent by the client is validated. If validation as ReferencePoint succeeds,
    the preferences of this particular user are updated. When all the preferences are in,
    the system begins the optimization and notifies all connected websockets that the
    optimization is done and the results are ready for fetching.

    If a user is not connected to the server, they will be notified when they connect next time.

    The server sends its data as text messages.

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
    
    if user.id not in group.user_ids:
        await websocket.send_text(f"User {user.username} doesn't belong in group {group.name}")
        await websocket.close()
        return
    
    if debug: 
        print(f"{user.username} has joined.")

    # Get the group manager object from the manager of group managers
    group_manager: GroupManager = await manager.get_group_manager(group_id=group_id)
    await group_manager.connect(user.id, websocket)
    if debug:
        print(group_manager.group_id)
        print(group_manager.sockets)
    while True:
        try:
            # Get data from socket
            data = await websocket.receive_text()
            data = ReferencePoint.model_validate(json.loads(data))
            # await group_manager.broadcast(message=f"{user_id_int}: {data}")
            # Validation successful, lets set the preferences.
            asyncio.create_task(
                group_manager.set_preference(user.id, data)
            )
        except ValidationError as e:
            print(f"ValidationError: {e}")
            continue
        except KeyError as e:
            print(f"KeyError: {e}")
            continue
        except json.decoder.JSONDecodeError as e:
            print(f"JSONDecoderError: {e}")
        except WebSocketDisconnect:
            await group_manager.disconnect(user.id, websocket)
            await group_manager.broadcast(message=f"{user.username} left.")
            if debug:
                print(group_manager.sockets)
                print(manager.group_managers)
            await manager.check_disconnect(group_id=group_id)
            break
        except RuntimeError as e:
            print(f"RuntimeError: {e}")
            break

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
    session.refresh(first_iteration)

    group.head_iteration = first_iteration
    session.add(group)
    session.commit()

    return JSONResponse(
        content={"message": f"Group with ID {group.id} created."},
        status_code=status.HTTP_201_CREATED
    )

@router.post("/initialize")
def initialize(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Initialize the problem with NIMBUS"""
    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if user.id != group.owner_id:
        raise HTTPException(
            detail=f"Unauthorized user",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    if group == None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    print(f"Groups head iterations parent: {group.head_iteration.parent}")
    if group.head_iteration.parent != None:
        raise HTTPException(
            detail=f"Group problem already initialized!",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    problem_db = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
    if problem_db == None:
        raise HTTPException(
            detail=f"No problem with id {group.problem_id} found!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    problem = Problem.from_problemdb(problem_db)

    #NOTE: NIMBUS METHOD
    starting_point: SolverResults = generate_starting_point(problem)
    iteration = group.head_iteration
    iteration.results = [starting_point]
    session.add(iteration)
    session.commit()
    session.refresh(iteration)

    new_iteration = GroupIteration(
        problem_id=iteration.problem_id,
        group_id=iteration.group_id,
        group=iteration.group,
        set_preferences={},
        results=[],
        notified={},
        parent_id=iteration.id,
        parent=iteration,
        child=None
    )

    session.add(new_iteration)
    session.commit()
    session.refresh(new_iteration)

    iteration.child = new_iteration
    session.add(iteration)
    group.head_iteration = new_iteration
    session.add(group)
    session.commit()

    return JSONResponse(
        content={"message": f"Group {group.id} initialized."},
        status_code=status.HTTP_200_OK
    )

@router.post("/delete_group")
def delete_group(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session : Annotated[Session, Depends(get_session)]
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
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found.",
            status_code=status.HTTP_404_NOT_FOUND
        )

    if user.id != group.owner_id:
        raise HTTPException(
            detail="Only the owner of a group may delete the group.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get the root iteration
    head: GroupIteration = group.head_iteration
    iter_count = 1
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
            detail="Couldn't delete group from the database!",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        

    return JSONResponse(
        content={
            "message": 
            f"Group with ID {request.group_id} and its {iter_count} iterations have been deleted."
        },
        status_code=status.HTTP_200_OK
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
            detail=f"There's no group with ID {request.group_id}",
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
            detail=f"User with ID {request.user_id} already in this group!",
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
            detail=f"No group with ID {request.group_id} found.",
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
            detail=f"User with ID {request.user_id} is not in this group!",
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

@router.post("/get_results")
def get_results(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> JSONResponse:
    """Get the latest results from group iteration

    Args:
        request (GroupInfoRequest): essentially just the ID of the group
        user (Annotated[User, Depends(get_current_user)]): current user
        session (Annotated[Session, Depends(get_session)])

    Returns:
        JSONResponse: A json response containing the latest results

    Raises:
        HTTPException: Validation errors or no results
    """
    group: Group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group == None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id} found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    if user.id not in group.user_ids:
        raise HTTPException(
            detail="Unauthorized user.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    nores_exp = HTTPException(
        detail="No results found!",
        status_code=status.HTTP_404_NOT_FOUND
    )

    try:
        iteration = group.head_iteration.parent
    except:
        raise nores_exp
    
    if iteration == None:
        raise nores_exp
    
    if iteration.results == None:
        raise nores_exp

    return JSONResponse(
        content={
            "results": [result.model_dump()["optimal_objectives"] for result in iteration.results]
        },
        status_code=status.HTTP_200_OK
    )