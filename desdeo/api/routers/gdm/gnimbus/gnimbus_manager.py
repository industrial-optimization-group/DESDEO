"""GNIMBUS group manager implementation. Handles varying paths of the GNIMBUS method."""

import copy
import json
import logging
import sys
from typing import Any

from pydantic import ValidationError
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import (
    BasePreferences,
    EndProcessPreference,
    GNIMBUSEndState,
    GNIMBUSOptimizationState,
    GNIMBUSVotingState,
    Group,
    GroupIteration,
    OptimizationPreference,
    ProblemDB,
    ReferencePoint,
    StateDB,
    VotingPreference,
)
from desdeo.api.routers.gdm.gdm_base import GroupManager
from desdeo.mcdm.gnimbus import solve_group_sub_problems, voting_procedure
from desdeo.problem import Problem
from desdeo.tools import SolverResults
from desdeo.tools.scalarization import ScalarizationError

logging.basicConfig(
    stream=sys.stdout, format="[%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class GNIMBUSManager(GroupManager):
    """The Group NIMBUS manager class.

    Implements Group NIMBUS functionality to the surrounding GDM framework.
    """

    # Repeated functionality collected into class methods
    async def set_and_update_preferences(
        self,
        user_id: int,
        preference: Any,
        preferences: BasePreferences,
        session: Session,
        current_iteration: GroupIteration,
    ):
        """Set and update preferences; write them into database."""
        preferences.set_preferences[user_id] = preference
        current_iteration.preferences = preferences
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)

    async def check_preferences(
        self,
        user_ids: list[int],
        preferences,
    ) -> bool:
        """Function to check if a preference item has all needed preferences."""
        for user_id in user_ids:
            try:
                # This shouldn't happen but just in case.
                if preferences.set_preferences[user_id] is None:
                    logger.info("Not all prefs in!")
                    return False
            except KeyError:
                logger.info("Key error: Not all prefs in!")
                return False
        return True

    async def get_state(self, session: Session, current_iteration: GroupIteration):
        """Get the current iteration's substate (GNIMBUSOptimizationState, ...VotingState, etc)."""
        prev_state: StateDB = session.exec(
            select(StateDB).where(StateDB.id == current_iteration.parent.state_id)
        ).first()
        if prev_state is None:
            print("No previous state!")
            return None
        return prev_state.state

    async def set_state(
        self,
        session: Session,
        problem_db: ProblemDB,
        optim_state: Any,  # Not really any but rather a state
        current_iteration: GroupIteration,
        user_ids: list[int],
        owner_id: int,
    ):
        """Add the state into database."""
        new_state = StateDB.create(
            database_session=session, problem_id=problem_db.id, session_id=None, parent_id=None, state=optim_state
        )

        session.add(new_state)
        session.commit()
        session.refresh(new_state)

        # Update state id to current iteration
        current_iteration.state_id = new_state.id
        session.add(current_iteration)
        session.commit()

        # notify connected users that the optimization is done
        g = user_ids
        g.append(owner_id)
        notified = await self.notify(
            user_ids=g, message=f"Please fetch {current_iteration.preferences.method} results."
        )

        # Update iteration's notifcation database item
        current_iteration.notified = notified
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)

    async def optimization(
        self,
        user_id: int,
        data: str,
        session: Session,
        group: Group,
        current_iteration: GroupIteration,
        problem_db: ProblemDB,
    ) -> VotingPreference | EndProcessPreference | None:
        """A function to handle the optimization path."""
        # we know the type of data we need so we'll validate the data as ReferencePoint.
        try:
            preference = ReferencePoint.model_validate(json.loads(data))
        except ValidationError:
            await self.send_message("Unable to validate sent data as reference point!", self.sockets[user_id])
            return None
        except json.decoder.JSONDecodeError:
            await self.send_message("Unable to decode data; make sure it is formatted properly.", self.sockets[user_id])
            return None
        except KeyError:
            await self.send_message(
                "Unable to validate data; make sure it is formatted properly.", self.sockets[user_id]
            )
            return None

        # Update the current GroupIteration's database entry with the new preferences
        # We need to do a deep copy here, otherwise the db entry won't be updated
        preferences: OptimizationPreference = copy.deepcopy(current_iteration.preferences)
        await self.set_and_update_preferences(
            user_id=user_id,
            preference=preference,
            preferences=preferences,
            current_iteration=current_iteration,
            session=session,
        )

        # Check if all preferences are in
        # There has to be a more elegant way of doing this
        preferences: OptimizationPreference = current_iteration.preferences
        if not await self.check_preferences(
            group.user_ids,
            preferences,
        ):
            return None

        # If all preferences are in, begin optimization.
        problem: Problem = Problem.from_problemdb(problem_db)
        prefs = current_iteration.preferences.set_preferences

        formatted_prefs = {}
        for key, item in prefs.items():
            formatted_prefs[key] = item.aspiration_levels
        logger.info(f"Formatted preferences: {formatted_prefs}")

        # And here we choose the first result of the previous iteration as the current objectives.
        # The previous solution could be perhaps voted, in a separate case of the surrounding match
        actual_state = await self.get_state(
            session,
            current_iteration,
        )
        if actual_state is None:
            return None

        prev_sol = actual_state.solver_results[0].optimal_objectives

        print(f"starting values: {prev_sol}")

        try:
            results: list[SolverResults] = solve_group_sub_problems(
                problem,
                current_objectives=prev_sol,
                reference_points=formatted_prefs,
                phase=current_iteration.preferences.phase,
            )
            logger.info(f"Optimization for group {self.group_id} done.")

        except ScalarizationError as e:
            await self.broadcast(f"Error while scalarizing: {e}")
            return None

        except Exception as e:
            await self.broadcast(f"An error occured while optimizing: {e}")
            return None

        optim_state = GNIMBUSOptimizationState(reference_points=formatted_prefs, solver_results=results)

        await self.set_state(session, problem_db, optim_state, current_iteration, group.user_ids, group.owner_id)

        # DIVERGE THE PATH: if we're in the decision phase, we'll want to see if everyone
        # is happy with the current solution, so we'll return end process preference.
        if current_iteration.preferences.phase == "decision":
            new_preferences = EndProcessPreference(set_preferences={}, success=None)
        # If we're in "learning" or "crp" phases, we return ordinary voting preference
        else:
            new_preferences = VotingPreference(set_preferences={})

        return new_preferences

    async def voting(
        self,
        user_id: int,
        data: str,
        session: Session,
        group: Group,
        current_iteration: GroupIteration,
        problem_db: ProblemDB,
    ) -> OptimizationPreference | None:
        """A function to handle voting path."""
        try:
            preference = int(data)
            if preference > 3 or preference < 0:
                await self.send_message("Voting index out of bounds! Can only vote for 0 to 3.", self.sockets[user_id])
                return None
        except Exception as e:
            print(e)
            await self.send_message("Unable to validate sent data as an integer!", self.sockets[user_id])
            return None

        preferences: VotingPreference = copy.deepcopy(current_iteration.preferences)
        await self.set_and_update_preferences(
            user_id=user_id,
            preference=preference,
            preferences=preferences,
            current_iteration=current_iteration,
            session=session,
        )

        # Check if all preferences are in
        preferences: VotingPreference = current_iteration.preferences
        if not await self.check_preferences(group.user_ids, preferences):
            return None

        formatted_votes = {}
        for key, value in preferences.set_preferences.items():
            formatted_votes[str(key)] = value

        problem: Problem = Problem.from_problemdb(problem_db)

        actual_state = await self.get_state(
            session,
            current_iteration,
        )
        if actual_state is None:
            return None

        results = actual_state.solver_results

        # Get the winning results
        winner_result: SolverResults = voting_procedure(
            problem=problem,
            solutions=results[-4:],  # we vote from the last 4 solutions, aka the common solutions
            votes_idxs=formatted_votes,
        )

        # Add winning result to database
        vote_state = GNIMBUSVotingState(votes=preferences.set_preferences, solver_results=[winner_result])

        await self.set_state(session, problem_db, vote_state, current_iteration, group.user_ids, group.owner_id)

        # Return a OptimizationPreferenceResult so
        # that we can fill it with reference points
        return OptimizationPreference(
            # really? I need to get the phase from the previous iteration?
            phase=current_iteration.parent.preferences.phase,
            set_preferences={},
        )

    async def ending(
        self,
        user_id: int,
        data: str,
        session: Session,
        group: Group,
        current_iteration: GroupIteration,
        problem_db: ProblemDB,
    ) -> OptimizationPreference | None:
        """Function to handle the ending path."""
        logger.info(f"incoming data: {data}")
        try:
            preference: bool = bool(int(data))
        except Exception:
            await self.send_message("Unable to validate sent data as an boolean value.", self.sockets[user_id])
            return None

        preferences: EndProcessPreference = copy.deepcopy(current_iteration.preferences)
        await self.set_and_update_preferences(
            user_id=user_id,
            preference=preference,
            preferences=preferences,
            current_iteration=current_iteration,
            session=session,
        )
        session.refresh(current_iteration)

        # Check if all preferences are in
        preferences: EndProcessPreference = current_iteration.preferences
        if not await self.check_preferences(
            group.user_ids,
            preferences,
        ):
            return None

        # All preferences in, let's see what they think.
        all_vote_yes: bool = True
        for uid in group.user_ids:
            if not preferences.set_preferences[uid]:
                all_vote_yes = False
                break
        new_copy_preferences: EndProcessPreference = copy.deepcopy(current_iteration.preferences)
        new_copy_preferences.success = all_vote_yes
        current_iteration.preferences = new_copy_preferences
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)
        print(current_iteration.preferences)

        actual_state = await self.get_state(
            session,
            current_iteration,
        )
        if actual_state is None:
            return None

        # We take the result that was voted on (there should be only one)
        results = actual_state.solver_results

        ending_state = GNIMBUSEndState(
            votes=current_iteration.preferences.set_preferences, solver_results=results, success=all_vote_yes
        )

        await self.set_state(session, problem_db, ending_state, current_iteration, group.user_ids, group.owner_id)

        # Return a OptimizationPreferenceResult so
        # that we can fill it with reference points
        return OptimizationPreference(
            phase=current_iteration.parent.preferences.phase,
            set_preferences={},
        )

    async def run_method(
        self,
        user_id: int,
        data: str,
    ):
        """The method function.

        Here, the preferences are set (and updated to database). If all preferences are set, optimize and
        update database with results. Then, create new iteration and assign the correct relationships
        between the database entries.

        The paths can hold whatever code one wants, but if done correctly, should result in updating data
        in the current iteration with preferences and results and after the "step" is done, the group's head
        should be updated to a new iteration, where one could the begin attaching new preferences.

        The flow of this specific method is the following:

        1.  phase: learning,    method: optimize
        2.  phase: learning,    method: voting
        3.  if switching phase to crp,
                go to 4.
            otherwise,
                go to 1.
        4.  phase: crp,         method: optimize
        5.  phase: crp,         method: voting
        6.  if switching phase to decision,
                go to 7.
            otherwise,
                go to 4.
        7.  phase: decision,    method: optimize
        8.  phase: decision,    method: end
        9.  if all voted "yes" on 8,
                end the process. (flagged item in database)
            otherwise,
                go to 7.
        """
        async with self.lock:
            # Fetch the current iteration
            session = next(get_session())
            group = session.exec(select(Group).where(Group.id == self.group_id)).first()
            if group is None:
                await self.broadcast(f"The group with ID {self.group_id} doesn't exist anymore.")
                session.close()
                return

            if group.head_iteration is None:
                await self.broadcast("Problem not initialized! Initialize the problem!")
                session.close()
                return

            current_iteration = group.head_iteration
            logger.info(f"Current iteration ID: {current_iteration.id}")

            problem_db: ProblemDB = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
            # This shouldn't be a problem at this point anymore, but
            if problem_db is None:
                await self.broadcast(f"There's no problem with ID {group.problem_id}!")
                return

            # Diverge into different paths using PreferenceResult method type of the current iteration.
            match current_iteration.preferences.method:
                case "optimization":
                    new_preferences = await self.optimization(
                        user_id=user_id,
                        data=data,
                        session=session,
                        group=group,
                        current_iteration=current_iteration,
                        problem_db=problem_db,
                    )

                case "voting":
                    # Here we could do some voting on the NIMBUS results.
                    new_preferences = await self.voting(
                        user_id=user_id,
                        data=data,
                        session=session,
                        group=group,
                        current_iteration=current_iteration,
                        problem_db=problem_db,
                    )

                case "end":
                    # throw an error
                    new_preferences = await self.ending(
                        user_id=user_id,
                        data=data,
                        session=session,
                        group=group,
                        current_iteration=current_iteration,
                        problem_db=problem_db,
                    )

                case _:
                    new_preferences = None
                    return

            if new_preferences is None:
                session.close()
                return

            # If everything has gone according to keikaku (keikaku means plan), create the next iteration.
            next_iteration = GroupIteration(
                group_id=self.group_id,
                group=group,
                problem_id=current_iteration.problem_id,
                preferences=new_preferences,
                notified={},
                parent_id=current_iteration.id,  # Probably redundant to have
                parent=current_iteration,  # two connections to parents?
                child=None,
            )
            session.add(next_iteration)
            session.commit()
            session.refresh(next_iteration)

            # Update new parent iteration
            current_iteration.child = next_iteration
            session.add(current_iteration)
            session.commit()

            # Update head of the group
            group.head_iteration = next_iteration
            session.add(group)
            session.commit()

            # Close the session
            session.close()
