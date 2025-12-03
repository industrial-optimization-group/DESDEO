"""GDM Score Bands manager implementation."""

import copy

import polars as pl
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import Group, GroupIteration, ProblemDB, User, GDMSCOREBandInformation
from desdeo.api.routers.gdm.gdm_base import GroupManager, ManagerError
from desdeo.tools.score_bands import SCOREBandsConfig, SCOREBandsResult, score_json


class GDMScoreBandsManager(GroupManager):
    """The group manager implementation for GDM Score Bands."""

    def __init__(self, group_id):
        """Initialize the group manager.

        Args:
            group_id (int): id of the group of this manager.
        """
        super().__init__(group_id)
        # LOAD THE DISCRETE REPRESENTATION
        session = next(get_session())
        group: Group = session.exec(select(Group).where(Group.id == group_id)).first()
        problem: ProblemDB = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
        if problem.discrete_representation is None:
            raise ManagerError("The group's discrete representation does not exist!")
        self.discrete_representation = problem.discrete_representation

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
        user: User,
        group: Group,
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
            group_iteration = session.exec(
                select(GroupIteration).where(GroupIteration.id == group.head_iteration_id)
            ).first()
            if group_iteration is None:
                raise ManagerError("No such Group Iteration! Did you initialize this group?")
            info_container = copy.deepcopy(group_iteration.info_container)
            if user.id in info_container.user_confirms:
                raise ManagerError("User has already confirmed they want to move on!")
            info_container.user_votes[user.id] = voted_index
            group_iteration.info_container = info_container
            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            # Then update preferences dictionary.
            await self.broadcast("UPDATE: A vote has been cast.")

    async def confirm(
        self,
        user: User,
        group: Group,
        session: Session
    ):
        """A method for a user to indicate that we could move forward with clustering anew.

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
            if user.id not in group.user_ids:
                raise ManagerError(
                    detail=f"User with ID {user.id} is not part of group with ID {group.id}",
                )
            group_iteration = session.exec(
                select(GroupIteration).where(GroupIteration.id == group.head_iteration_id)
            ).first()
            if group_iteration is None:
                raise ManagerError("No such Group Iteration! Did you initialize this group?")

            info_container = copy.deepcopy(group_iteration.info_container)
            if user.id not in info_container.user_votes:
                raise ManagerError("User hasn't voted! Cannot confirm!")
            # if user.id in info_container.user_confirms:
                raise ManagerError("User has already confirmed they want to move on!")
            info_container.user_confirms.append(user.id)
            group_iteration.info_container = info_container
            session.add(group_iteration)
            session.commit()
            session.refresh(group_iteration)

            # After everyone's done, filter etc.
            for uid in group.user_ids:
                # Check if user is not in the list of confirms
                if uid not in info_container.user_confirms:
                    return

            # Every user seems to have wanted to move on.
            # See which band has won
            votes = [x for _, x in info_container.user_votes.items()]
            band_ids = set(info_container.score_bands_result.clusters)
            vote_counts = [votes.count(i) for i in band_ids]
            winners = []
            max_votes = max(vote_counts)
            for i in band_ids:
                if vote_counts[i - 1] == max_votes:
                    winners.append(i)

            print(f"Winning bands: {winners}")
            # Now we have the winning bands, and now we filter the active indices with them.

            active_indices = info_container.active_indices
            clusters = info_container.score_bands_result.clusters

            # Into polars data frame for neater handling
            indices_and_clusters_df = pl.DataFrame({"index": active_indices, "cluster": clusters})

            # Filter using the winners list
            indices_and_clusters_df = indices_and_clusters_df.filter(pl.col("cluster").is_in(winners))

            # Get them objective values with indices on them
            active_repr = self.discrete_representation.objective_values
            objective_keys = list(active_repr)
            objs = pl.DataFrame(active_repr).with_row_index()

            # Join the two lists: basically if an index exists in indices_and_clusters_df,
            # select the corresponding row from objs.
            objs_w_indices = indices_and_clusters_df.join(
                other=objs,
                how="left",
                left_on="index",
                right_on="index"
            )

            # Get just the objectives.
            objs = objs_w_indices.select(objective_keys)

            # We use the latest core bands config by default. Cluster the stuff.
            # TODO: figure how to change that.
            score_bands_config = info_container.score_bands_config
            result: SCOREBandsResult = score_json(
                data=objs,
                options=score_bands_config
            )

            # store necessary data to the database. Currently all "voting" related is null bc no voting has happened yet
            score_bands_info = GDMSCOREBandInformation(
                user_votes={},
                user_confirms=[],
                voting_results=None,
                active_indices=objs_w_indices.to_dict(as_series=False)["index"],
                score_bands_config=score_bands_config,
                score_bands_result=result
            )

            # Add group iteration and related stuff, then set new iteration to head.
            new_iteration: GroupIteration = GroupIteration(
                group_id=group.id,
                problem_id=group.problem_id,
                info_container=score_bands_info,
                notified={},
                state_id=None,
                parent_id=group.head_iteration_id,
                parent=group_iteration,
            )

            session.add(new_iteration)
            session.commit()
            session.refresh(new_iteration)

            group.head_iteration_id = new_iteration.id
            session.add(group)
            session.commit()
            session.refresh(group)

            await self.broadcast("UPDATE: A new iteration has begun.")
