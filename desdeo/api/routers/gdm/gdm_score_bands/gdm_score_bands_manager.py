"""GDM Score Bands manager implementation."""

from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import Group, GroupIteration, ProblemDB
from desdeo.api.routers.gdm.gdm_base import GroupManager, ManagerError
from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult


class GDMScoreBandsManager(GroupManager):
    """The group manager implementation for GDM Score Bands."""

    def __init__(self, group_id):
        """Initialize the group manager.

        Args:
            group_id (int): id of the group of this manager.
        """
        super().__init__(group_id)


    async def run_method(self, user_id: int, data: str):
        """Method runner implementation for GDM Score Bands.

        Args:
            user_id (int): The user's ID this data is from.
            data (str): The data itself. To be validated.
            WE MIGHT NOT EVEN NEED THIS!!
        """
        async with self.lock:
            await self.send_message(
                "THIS METHOD IS USED THROUGH THE APPROPRIATE HTTP ENDPOINTS!",
                self.sockets[user_id]
            )

    async def vote(
        self,
        user_id: int,
        group_id: int,
        voted_index: int,
        session: Session
    ):
        """A method for voting on a specific band.

        Use this from an actual HTTP endpoint and not in a
        stupid websocket way like in GNIMBUS. Every time this is
        operated, send all connected websockets info on the voting.

        Args:
            user_id (int): User's identification number
            voted_index (int): the vote
            session: (Session) the database session.
        """
        async with self.lock: #not sure if async lock is all that necessary but here we go anyways.
            # TODO!!!
            # Get group and latest iteration.
            # Then update preferences dictionary.
            await self.broadcast(f"OH YEAH BROTHER! UID: {user_id}, GID: {group_id}, VOTE: {voted_index}")

    async def confirm(
        self,
        user_id: int,
        group_id: int,
        session: Session
    ):
        """A method for a user to use that we could move forward with clustering anew.

        After everyone has hit this endpoint, do the following shenanigans:
            1. Filter the active solution indices using the voting result.
            2. Create a new GroupIteration.
            3. Re-cluster the active solutions and put the result into the
               preference item of the newly created GroupIteration.
            4. Send all connected websockets info that we've got some hot
               new data to update the UI with. Then use some other endpoint to
               fetch that data.

        Args:
            user_id (int): The user's id number.
            group_id (int): The group's id number.
            session (Session): The database session.
        """
        async with self.lock:
            # TODO!
            # Everything.
            pass
