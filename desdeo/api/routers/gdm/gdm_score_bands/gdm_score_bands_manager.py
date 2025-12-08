"""GDM Score Bands manager implementation."""

import copy

import polars as pl
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    GDMSCOREBandFinalSelection,
    GDMSCOREBandInformation,
    Group,
    GroupIteration,
    ProblemDB,
    User,
)
from desdeo.api.routers.gdm.gdm_base import GroupManager, ManagerError
from desdeo.gdm.score_bands import SCOREBandsGDMConfig, SCOREBandsGDMResult, score_bands_gdm
from desdeo.gdm.voting_rules import consensus_rule, majority_rule
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
        session.close()

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
            #if user.id in info_container.user_confirms:
            #    raise ManagerError("User has already confirmed they want to move on!")
            info_container.user_votes[str(user.id)] = voted_index
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
               info_container item of the newly created GroupIteration.
            4. Send all connected websockets info that we've got some hot
               new data to update the UI with. Then use some other endpoint to
               fetch that data.

        Args:
            user (User): The user
            group (Group): The group
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
                raise ManagerError("No group iterations! Did you initialize this group?")

            info_container = copy.deepcopy(group_iteration.info_container)
            if str(user.id) not in info_container.user_votes:
                raise ManagerError("User hasn't voted! Cannot confirm!")
            #if user.id in info_container.user_confirms:
                raise ManagerError("User has already confirmed they want to move on!")
            if user.id not in info_container.user_confirms:
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

            # We're in consensus reaching phase
            if info_container.method == "gdm-score-bands":

                # Seems like every user wants to move on.
                statement = select(GroupIteration)\
                    .where(GroupIteration.group_id == group.id)
                iterations: list[GroupIteration] = session.exec(statement).all()
                state: list[SCOREBandsGDMResult] = [iteration.info_container.score_bands_result \
                                                    for iteration in iterations if \
                                                        iteration.info_container.method == "gdm-score-bands"]
                for st in state:
                    print(f"{st.iteration}: {len(st.score_bands_result.clusters)}")

                # USE Bhupinder's score bands stuff.
                score_bands_config = SCOREBandsGDMConfig(
                    score_bands_config=info_container.score_bands_config.score_bands_config,
                    from_iteration=state[-1].iteration # the ID from the latest iteration.
                )

                # Get them discrete reprs
                discrete_repr = self.discrete_representation

                # Make sure that there are enough solutions for re-clustering
                votes = group_iteration.info_container.user_votes
                winners = consensus_rule(votes, score_bands_config.minimum_votes)
                relevant_ids = state[-1].relevant_ids
                clustering = state[-1].score_bands_result.clusters
                if len([x[0] for x in zip(relevant_ids, clustering, strict=True) if x[1] in winners]) < 11:
                    print("LESS THAN OR AS MUCH AS 10")
                    # THERE ARE 10 OR LESS SOLUTIONS IN TOTAL: MOVE ON TO DECISION PHASE!

                    obj_keys = list(discrete_repr.objective_values)
                    var_keys = list(discrete_repr.variable_values)

                    objs = pl.DataFrame(discrete_repr.objective_values).with_row_index()
                    varis = pl.DataFrame(discrete_repr.variable_values)
                    indices = pl.DataFrame({
                        "index": relevant_ids,
                        "cluster": clustering
                    }).filter(pl.col("cluster").is_in(winners))
                    objs = indices.join(
                        other=objs,
                        how="left",
                        left_on="index",
                        right_on="index"
                    ).select(obj_keys)
                    varis = indices.join(
                        other=varis,
                        how="left",
                        left_on="index",
                        right_on="index"
                    ).select(var_keys)

                    info_container = GDMSCOREBandFinalSelection(
                        user_votes={},
                        user_confirms=[],
                        solution_variables=varis.to_dict(),
                        solution_objectives=objs.to_dict(),
                        winner_solution_variables={},
                        winner_solution_objectives={},
                    )

                else:
                    print("MORE THAN 10")
                    discrete_repr = discrete_repr.objective_values
                    objective_keys = list(discrete_repr)
                    objs = pl.DataFrame(discrete_repr).with_row_index()
                    objs = objs.select(objective_keys)

                    result: list[SCOREBandsGDMResult] = score_bands_gdm(
                        data=objs,
                        config=score_bands_config,
                        state=state,
                        votes=votes
                    )

                    # store necessary data to the database. Currently all "voting" related is null bc no voting has happened
                    info_container = GDMSCOREBandInformation(
                        user_votes={},
                        user_confirms=[],
                        score_bands_config=score_bands_config,
                        score_bands_result=result[-1]
                    )


                # Add group iteration and related stuff, then set new iteration to head.
                new_iteration: GroupIteration = GroupIteration(
                    group_id=group.id,
                    problem_id=group.problem_id,
                    info_container=info_container,
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

            # We're in decision phase.
            elif info_container.method == "gdm-score-bands-final":

                winner = majority_rule(info_container.user_votes) # A different rule perhaps?
                #if len(winners) > 1:
                #    pass # TODO: minimize distance or whatever

                varis = info_container.solution_variables
                vari_keys = list(varis)
                objs = info_container.solution_objectives
                obj_keys = list(objs)

                vari_d = {}
                for key in vari_keys:
                    vari_d[key] = varis[key][winner]
                print(vari_d)

                obj_d = {}
                for key in obj_keys:
                    obj_d[key] = objs[key][winner]
                print(obj_d)

                info_container.winner_solution_variables = vari_d
                info_container.winner_solution_objectives = obj_d

                group_iteration.info_container = info_container

                session.add(group_iteration)
                session.commit()

    async def revert(
        self,
        user: User,
        group: Group,
        session: Session,
        group_iteration_number: int
    ):
        """Revert to a different iteration.

        Args:
            user (User): Current user
            group (Group): Current group
            session (Session): database session
            iteration_number (int): the iteration to which we want to revert.

        Raises:
            ManagerError
        """
        async with self.lock:
            group_iteration = session.exec(
                select(GroupIteration).where(GroupIteration.id == group.head_iteration_id)
            ).first()
            if group_iteration is None:
                raise ManagerError("No group iterations! Did you initialize this group?")

            statement = select(GroupIteration)\
                .where(GroupIteration.group_id == group.id)
            iterations: list[GroupIteration] = session.exec(statement).all()

            target_group_iteration: GroupIteration = [i for i in iterations if i.id == group_iteration_number][0]

            state: list[SCOREBandsGDMResult] = [
                iteration.info_container.score_bands_result for iteration in \
                iterations if iteration.info_container.method == "gdm-score-bands"
            ]

            prev_id = state[-1].iteration
            result = target_group_iteration.info_container.score_bands_result
            result.previous_iteration = prev_id
            result.iteration = prev_id + 1

            info_container = GDMSCOREBandInformation(
                user_votes={},
                user_confirms=[],
                score_bands_config=target_group_iteration.info_container.score_bands_config,
                score_bands_result=result
            )

            # Add group iteration and related stuff, then set new iteration to head.
            new_iteration: GroupIteration = GroupIteration(
                group_id=group.id,
                problem_id=group.problem_id,
                info_container=info_container,
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

            await self.broadcast("UPDATE: Iteration reverted.")
