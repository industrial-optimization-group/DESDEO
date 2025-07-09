import asyncio

from fastapi import (
    APIRouter, 
    WebSocket, 
    WebSocketDisconnect, 
    Depends
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import HTTPException, status

from sqlmodel import Session, select
from typing import Annotated, Any

from desdeo.api.models import User, Group, GroupAddRequest, GroupCreateRequest
from desdeo.api.db import get_session
from desdeo.api.routers.user_authentication import get_current_user

class ManagerException(Exception):
    """If something goes awry with the manager"""

router = APIRouter(prefix="/gdm")

debug = True

usrs = {
    1: ["matti", "pekka"],
    2: ["teppo", "teuvo"],
}

class GroupManager:
    """A group manager. Manages connections, disconnections, optimization and communication to users."""


    def __init__(self, group_id: int):

        self.lock = asyncio.Lock()
        self.group_id: int = group_id
        self.session = next(get_session())
        self.group = self.session.exec(select(Group).where(Group.id == group_id)).first()
        if self.group == None:
            raise ManagerException(f"No group with ID {group_id} found!")

        self.usrs = usrs[group_id] ## DUMMY VALUES


        self.active_group_session: dict[str, dict[str, Any]] = {}

        # Load iteration-specific existing preferences from database?
        # Check which iteration we're dealing with


    async def connect(
        self,
        user: str,
        websocket: WebSocket
    ):
        await websocket.accept()
        try:
            self.active_group_session[user]["socket"] = websocket
        except KeyError:
            if debug:
                print("new user!")
            self.active_group_session[user] = {}
            self.active_group_session[user]["socket"] = websocket


    async def disconnect(
        self, 
        user: str,
        websocket: WebSocket
    ):
        try:
            if self.active_group_session[user]["socket"] == websocket:
                self.active_group_session[user]["socket"] = None
        except KeyError:
            if debug:
                print("Empty group!")


    async def broadcast(self, message: str):
        if self.active_group_session != {}:
            for user, dictionary in self.active_group_session.items():
                try:
                    await dictionary["socket"].send_text(message)
                except:
                    if debug:
                        print(f"Socket of user {user} is closed")


    # A dummy for implementing actual optimization
    async def run_optim(self):
        # Synthesize preferences, details are method specific
        await asyncio.sleep(1)
        message = ""
        for usr, dictionary in self.active_group_session.items():
            message = message + f"{usr} : {dictionary["preference"]}; "
        await self.broadcast(message)

        # Optimize 
        await asyncio.sleep(7)
        await self.broadcast("optimizin' done")
        print(f"Optimization for group {self.group_id} done.")

        # ADD optimization results into database


    async def set_preference(self, user: str, data: str):
        async with self.lock:
            session = next(get_session())
            statement = select(Group).where(Group.id == self.group_id)
            test = session.exec(statement).first()
            print(test.name)
            # Add preferences to user (and also into database I believe?)
            self.active_group_session[user]["preference"] = data
            for usr in self.usrs:
                try:
                    if self.active_group_session[usr]["preference"] == None:
                        return
                except:
                    return
            # If all preferences are in
            await self.run_optim()
            for usr, dictionary in self.active_group_session.items():
                dictionary["preference"] = None


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
            empty = True
            for _, dictionary in group_manager.active_group_session.items():
                if dictionary["socket"] != None:
                    empty = False
            if empty:
                async with group_manager.lock:
                    try:
                        del self.group_managers[group_id]
                    except:
                        if debug:
                            print(f"Group {group_id} already deleted!")


manager = ManagerManager()


@router.post("/create_group")
def create_group(
    request: GroupCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> JSONResponse:
    """Suppose a group is attached to only one problem. Does that make any sense?"""
    group = Group(
        owner_id=user.id,
        user_ids=[],
        problem_id=request.problem_id,
        name=request.group_name
    )

    session.add(group)
    session.commit()
    session.refresh(group)

    return JSONResponse(
        content={"message": f"Group with ID {group.id} created."},
        status_code=status.HTTP_201_CREATED
    )

@router.post("/add_to_group")
def join_group(
    request: GroupAddRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> JSONResponse:
    group: Group = session.exec(select(Group).where(Group.id == request.id))
    if group == None:
        raise HTTPException(
            detail="There's no such group!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    if not group.owner_id == user.id:
        raise HTTPException(
            detail="Unauthorized user",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    group.user_ids.append(request.user_id)
    session.add(group)
    session.commit()
    return JSONResponse(
        content={"message": f"Added user {request.user_id} to group {request.group_id}."},
        status_code=status.HTTP_200_OK
    )

@router.post("/get_results")
def get_results(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> Any:
    pass


@router.websocket("/ws/{group_id}/{user_name}")
async def websocket_endpoint(
    group_id: str,
    user_name: str,
    session: Annotated[Session, Depends(get_session)],
    websocket: WebSocket,
):
    group_id_int = int(group_id) + 1
    group = session.exec(select(Group).where(Group.id == group_id)).first()
    if group == None:
        raise HTTPException(
            detail=f"No group with ID {group_id} found!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    # Validate user or something.
    group_manager = await manager.get_group_manager(group_id=group_id_int)
    await group_manager.connect(user_name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await group_manager.broadcast(message=f"{user_name}: {data}")
            if data.startswith("pref: "):
                asyncio.create_task(group_manager.set_preference(user_name, data[5:]))
    except WebSocketDisconnect:
        await group_manager.disconnect(user_name, websocket)
        await group_manager.broadcast(message=f"{user_name} left the chat")
        if debug:
            print(group_manager.active_group_session)
            print(manager.group_managers)
        await manager.check_disconnect(group_id=group_id_int)
