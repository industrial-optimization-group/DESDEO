import asyncio

from fastapi import (
    APIRouter, 
    WebSocket, 
    WebSocketDisconnect, 
    Depends
)
from fastapi.responses import HTMLResponse

from sqlmodel import Session, SQLModel
from typing import Annotated, Any

from desdeo.api.models import User, Group, GroupSessionJoinRequest
from desdeo.api.db import get_session
from desdeo.api.routers.user_authentication import get_current_user

router = APIRouter(prefix="/gdm")

debug = True

usrs = {
    0: ["matti", "pekka"],
    1: ["teppo", "teuvo"]        
}


class GroupManager:
    """A group manager. Manages connections, disconnections, optimization and communication to users."""

    group_id: int
    usrs: list[str]
    active_group_session: dict[str, dict[str, Any]]
    optimizing: bool
    session: Session


    def __init__(self, group_id: int):
        self.usrs = usrs[group_id]
        self.group_id: int = group_id
        self.active_group_session: dict[User, dict[str, Any]] = {}
        self.optimizing: bool = False
        self.session = get_session()

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
                print("no group!")
            self.active_group_session[user] = {}
            self.active_group_session[user]["socket"] = websocket


    async def disconnect(
        self, 
        user: str,
    ):
        try:
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
        # Check if optimization is already in process
        if self.optimizing:
            print("I'm optimizin'!")
            return
        self.optimizing = True
        
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

        # We're not optimizing any more
        self.optimizing = False


    async def set_preference(self, user: str, data: str):
        # check if optimizing is already in progress
        if self.optimizing:
            print("I'm optimizin'!")
            return
        
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
    """A class to manage group managers. Spawns them and deletes them. Stupid name, I know."""

    group_managers: dict[int, GroupManager]

    def __init__(self):
        self.group_managers: dict[int, GroupManager] = {}

    async def get_group_manager(self, group_id: int) -> GroupManager:
        """Get the group manager for a specific group. If it doesn't exist, create one."""
        try:
            return self.group_managers[group_id]
        except:
            group_manager = GroupManager(group_id=group_id)
            self.group_managers[group_id] = group_manager
            return group_manager
        
    async def check_disconnect(self, group_id: int):
        """If no active connections, remove group manager"""
        group_manager = self.group_managers[group_id]
        empty = True
        for user, dictionary in group_manager.active_group_session.items():
            if dictionary["socket"] != None:
                empty = False
        while group_manager.optimizing:
            await asyncio.sleep(5)
        if empty:
            try:
                del self.group_managers[group_id]
            except:
                if debug:
                    print(f"Group {group_id} already deleted!")


manager = ManagerManager()


# Not needed as of now
@router.post("/join")
async def join_gdm_session(
    request: GroupSessionJoinRequest,
    user: str
) -> HTMLResponse:
    pass


@router.websocket("/ws/{group_id}/{user_name}")
async def websocket_endpoint(
    group_id: str,
    user_name: str,
    websocket: WebSocket,
):
    group_id_int = int(group_id)
    group_manager = await manager.get_group_manager(group_id=group_id_int)
    await group_manager.connect(user_name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await group_manager.broadcast(message=f"{user_name}: {data}")
            if data.startswith("pref: "):
                asyncio.create_task(group_manager.set_preference(user_name, data[5:]))
    except WebSocketDisconnect:
        await group_manager.disconnect(user_name)
        await group_manager.broadcast(message=f"{user_name} left the chat")
        if debug:
            print(group_manager.active_group_session)
            print(manager.group_managers)
        await manager.check_disconnect(group_id=group_id_int)
    """
    except RuntimeError:
        # Kinda wish websockets would have more nuanced errors...
        # Is this unholy? Cursed even? Probably.
        print(f"User {user_name} disconnected.")
    """