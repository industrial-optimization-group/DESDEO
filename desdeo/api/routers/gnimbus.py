"""GNIMBUS router implementation"""

import logging
import json
import copy
import sys
logging.basicConfig(
    stream=sys.stdout,
    format='[%(filename)s:%(lineno)d] %(levelname)s: %(message)s',
    level=logging.INFO
)

from fastapi import (
    APIRouter,
    Depends,
)

from fastapi.responses import JSONResponse
from fastapi import HTTPException, status

from sqlmodel import Session, select
from pydantic import ValidationError
from typing import Annotated

from desdeo.api.models import (
    User, 
    Group, 
    GroupIteration,
    GroupInfoRequest,
    ProblemDB,
    ReferencePoint,
    StateDB,
    GNIMBUSOptimizationState,
    GNIMBUSVotingState,
    SolutionReference,
)
from desdeo.api.db import get_session
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.problem import Problem

from desdeo.mcdm.nimbus import generate_starting_point
from desdeo.mcdm.gnimbus import solve_sub_problems, voting_procedure

from desdeo.tools import SolverResults
from desdeo.tools.scalarization import ScalarizationError

from desdeo.api.routers.gdm_base import GroupManager
from desdeo.api.models.gnimbus import (
    OptimizationPreference,
    VotingPreference,
    GNIMBUSResultResponse,
    FullIteration,
    GNIMBUSAllIterationsResponse,
)

router = APIRouter(prefix="/gnimbus")

class GNIMBUSManager(GroupManager):

    async def optimization(
            self,
            user_id: int,
            data: str,
            session: Session,
            group: Group,
            current_iteration: GroupIteration,
    ) -> VotingPreference | None:
        """A function to handle the NIMBUS path"""

        # we know the type of data we need so we'll validate the data as ReferencePoint.
        try:
            preference = ReferencePoint.model_validate(json.loads(data))
        except ValidationError as e:
            await self.send_message(f"Unable to validate sent data as reference point!", self.sockets[user_id])
            return None
        except json.decoder.JSONDecodeError as e:
            await self.send_message(f"Unable to decode data; make sure it is formatted properly.", self.sockets[user_id])
            return None
        except KeyError as e:
            await self.send_message(f"Unable to validate data; make sure it is formatted properly.", self.sockets[user_id])
            return None

        # Update the current GroupIteration's database entry with the new preferences
        # We need to do a deep copy here, otherwise the db entry won't be updated
        preferences: OptimizationPreference = copy.deepcopy(current_iteration.preferences)
        preferences.set_preferences[user_id] = preference
        current_iteration.preferences = preferences
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)

        # Check if all preferences are in
        # There has to be a more elegant way of doing this
        preferences: OptimizationPreference = current_iteration.preferences
        for user_id in group.user_ids:
            try:
                # This shouldn't happen but just in case.
                if preferences.set_preferences[user_id] == None:
                    logging.info("Not all prefs in!")
                    return None
            except KeyError:
                logging.info("Key error: Not all prefs in!")
                return None
        
        # If all preferences are in, begin optimization.
        problem_db: ProblemDB = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
        problem: Problem = Problem.from_problemdb(problem_db)
        prefs = current_iteration.preferences.set_preferences
        
        formatted_prefs = {}
        for key, item in prefs.items():
            formatted_prefs[str(key)] = item.aspiration_levels
        logging.info(f"Formatted preferences: {formatted_prefs}")

        # And here we choose the first result of the previous iteration as the current objectives.
        # The previous solution could be perhaps voted, in a separate case of the surrounding match
        prev_state: StateDB = session.exec(select(StateDB).where(StateDB.id == current_iteration.parent.state_id)).first()
        if prev_state == None:
            print("No previous state!")
            return None
        actual_prev_state: GNIMBUSVotingState = prev_state.state

        prev_sol = actual_prev_state.solver_results[0].optimal_objectives
        logging.info(f"Previous solution: {prev_sol}")

        try:
            results: list[SolverResults] = solve_sub_problems(
                problem,
                current_objectives=prev_sol,
                reference_points=formatted_prefs,
                phase=current_iteration.preferences.phase,
            )
            logging.info(f"Optimization for group {self.group_id} done.")

        except ScalarizationError as e:
            await self.broadcast(f"Error while scalarizing: {e}")
            return None

        except Exception as e:
            await self.broadcast(f"An error occured while optimizing: {e}")
            return None
        
        # TODO: Create StateDB and store the results there. Also 
        # connect the state to the right group iteration

        optim_state = GNIMBUSOptimizationState(
            reference_points=formatted_prefs,
            solver_results=results
        )

        new_state = StateDB.create(
            database_session=session,
            problem_id=problem_db.id,
            session_id=None,
            parent_id=None,
            state=optim_state
        )

        session.add(new_state)
        session.commit()
        session.refresh(new_state)

        # Update state id to current iteration
        current_iteration.state_id = new_state.id
        session.add(current_iteration)
        session.commit()

        # If the optimization succeeds, update the iteration and
        # notify connected users that the optimization is done
        notified = await self.notify(user_ids=group.user_ids, message="Please fetch results.")
        
        # Update iteration's notifcation database item
        current_iteration.notified = notified
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)

        # Make a preference result for putting in the voting preferences
        new_preferences = VotingPreference(
            set_preferences={}
        )

        return new_preferences
    
    async def voting(
        self,
        user_id: int,
        data: str,
        session: Session,
        group: Group,
        current_iteration: GroupIteration,
    ) -> OptimizationPreference | None:
        """ A function to handle voting path """

        try:
            preference = int(data)
        except Exception as e:
            print(e)
            await self.send_message(f"Unable to validate sent data as an integer!", self.sockets[user_id])
            return None

        preferences: VotingPreference = copy.deepcopy(current_iteration.preferences)
        preferences.set_preferences[user_id] = preference
        current_iteration.preferences = preferences
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)

        print(preferences)

        # Check if all preferences are in
        preferences: VotingPreference = current_iteration.preferences
        for user_id in group.user_ids:
            try:
                # This shouldn't happen but just in case.
                if preferences.set_preferences[user_id] == None:
                    logging.info("Not all prefs in!")
                    return None
            except KeyError:
                logging.info("Key error: Not all prefs in!")
                return None

        formatted_votes = {}
        for key, value in preferences.set_preferences.items():
            formatted_votes[str(key)] = value


        problem_db: ProblemDB = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
        problem: Problem = Problem.from_problemdb(problem_db)

        prev_state = session.exec(select(StateDB).where(StateDB.id == current_iteration.parent.state_id)).first()
        if prev_state == None:
            print("No previous state?")
            return None

        actual_state = prev_state.state
        results = actual_state.solver_results

        # Get the winning results
        winner_result: SolverResults = voting_procedure(
            problem=problem,
            solutions=results[-4:], # we vote from the last 4 solutions, aka the common solutions
            votes_idxs=formatted_votes
        )

        # Add winning result to database
        vote_state = GNIMBUSVotingState(
            votes=preferences.set_preferences,
            solver_results=[winner_result]
        )

        new_state = StateDB.create(
            database_session=session,
            problem_id=problem_db.id,
            session_id=None,
            parent_id=None,
            state=vote_state
        )

        session.add(new_state)
        session.commit()
        session.refresh(new_state)

        # Update iteration's state id
        current_iteration.state_id = new_state.id
        session.add(current_iteration)
        session.commit()

        # If the optimization succeeds, update the iteration and
        # notify connected users that the optimization is done
        notified = await self.notify(user_ids=group.user_ids, message="Voting has concluded.")
        
        # Update iteration's notifcation database item
        current_iteration.notified = notified
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)

        # Return a OptimizationPreferenceResult so
        # that we can fill it with reference points
        new_preferences = OptimizationPreference(
            set_preferences={},
        )
    
        return new_preferences


    async def run_method(
            self,
            user_id: int,
            data: str,
    ):
        """The method function.
        
        Here, the preferences are set (and updated to database). If all preferences are set, optimize and
        update database with results. Then, create new iteration and assign the correct relationships
        between the database entries.

        This serves as an example on how this system could be utilized and how the diverging of the 
        paths could be handled (i.e. making multi-phase gdm). We could have two types of "paths", first one beign the 
        NIMBUS path and the second one beign the voting path. The execution path taken is determined by the
        method field of pref_result of the group's head iteration.

        The paths can hold whatever code one wants, but if done correctly, should result in updating data
        in the current iteration with preferences and results and after the "step" is done, the group's head
        should be updated to a new iteration, where one could the begin attaching new preferences/results.
        """

        async with self.lock:

            # Fetch the current iteration
            session = next(get_session())
            group = session.exec(select(Group).where(Group.id == self.group_id)).first()
            if group == None:
                await self.broadcast(f"The group with ID {self.group_id} doesn't exist anymore.")
                session.close()
                return

            if group.head_iteration == None:
                await self.broadcast("Problem not initialized! Initialize the problem!")
                session.close()
                return

            current_iteration = group.head_iteration
            logging.info(f"Current iteration ID: {current_iteration.id}")

            # Diverge into different paths using PreferenceResult method type of the current iteration.
            match current_iteration.preferences.method:
                case "optimization":
                    new_preferences = await self.optimization(
                        user_id=user_id,
                        data=data,
                        session=session,
                        group=group,
                        current_iteration=current_iteration
                    )

                case "voting":
                    # Here we could do some voting on the NIMBUS results.
                    new_preferences = await self.voting(
                        user_id=user_id,
                        data=data,
                        session=session,
                        group=group,
                        current_iteration=current_iteration
                    )

                case _:
                    # throw an error
                    new_preferences = None
                    return
            
            if new_preferences == None:
                session.close()
                return
            
            # If everything has gone according to keikaku (keikaku means plan), create the next iteration.
            next_iteration = GroupIteration(
                group_id=self.group_id,
                group=group,
                problem_id=current_iteration.problem_id,
                preferences=new_preferences,
                notified={},
                parent_id=current_iteration.id, # Probably redundant to have
                parent=current_iteration,       # two connections to parents?
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


@router.post("/initialize")
def gnimbus_initialize(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Initialize the problem for NIMBUS
    
    Different initializations should be used for different methods
    """
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
    
    if group.head_iteration != None:
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

    # Create the first iteration for the group
    # As if we just voted for a result, but really is just the starting point.
    starting_point = generate_starting_point(problem)

    gnimbus_state = GNIMBUSVotingState(
        votes={},
        solver_results=[starting_point]
    )

    state = StateDB.create(
        database_session=session,
        problem_id=problem_db.id,
        session_id=None,
        parent_id=None,
        state=gnimbus_state
    )

    session.add(state)
    session.commit()
    session.refresh(state)

    start_iteration = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        group=group,
        preferences=VotingPreference(
            set_preferences={},
        ),
        notified={},
        state_id=state.id,
        parent_id=None,
        parent=None,
        child=None
    )

    session.add(start_iteration)
    session.commit()
    session.refresh(start_iteration)

    new_iteration = GroupIteration(
        problem_id=start_iteration.problem_id,
        group_id=start_iteration.group_id,
        group=start_iteration.group,
        preferences=OptimizationPreference(
            set_preferences={},
        ),
        notified={},
        parent_id=start_iteration.id,
        parent=start_iteration,
        child=None
    )

    session.add(new_iteration)
    session.commit()
    session.refresh(new_iteration)

    start_iteration.child = new_iteration
    session.add(start_iteration)
    group.head_iteration = new_iteration
    session.add(group)
    session.commit()

    return JSONResponse(
        content={"message": f"Group {group.id} initialized."},
        status_code=status.HTTP_200_OK
    )


@router.post("/get_latest_results")
def get_latest_results(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> GNIMBUSResultResponse:
    """Get the latest results from group iteration

    Args:
        request (GroupInfoRequest): essentially just the ID of the group
        user (Annotated[User, Depends(get_current_user)]): current user
        session (Annotated[Session, Depends(get_session)])

    Returns:
        JSONResponse: A json response containing the latest gnimbus results

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
    
    state = session.exec(select(StateDB).where(StateDB.id == iteration.state_id)).first()
    if state == None:
        raise nores_exp
    
    actual_state = state.state
    preferences = iteration.preferences

    if type(actual_state) == GNIMBUSVotingState:
        return GNIMBUSResultResponse(
            method="voting",
            phase=iteration.parent.preferences.phase if iteration.parent is not None else "learning",
            preferences = preferences,
            common_results=[SolutionReference(state=state, solution_index=0)],
            user_results=[],
            personal_result_index=None,
        )

    personal_result_index = None
    for i, item in enumerate(preferences.set_preferences.items()):
        if item[0] == user.id:
            personal_result_index = i
            break

    if personal_result_index == None:
        raise HTTPException(
            detail=f"No personal results for user ID {user.id}",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    solution_references = []
    for i, _ in enumerate(actual_state.solver_results):
        solution_references.append(SolutionReference(state=state, solution_index=i))

    return GNIMBUSResultResponse(
        method="optimization",
        phase=iteration.preferences.phase,
        preferences=preferences,
        common_results=solution_references[-4:],
        user_results=solution_references[:-4],
        personal_result_index=personal_result_index,
    )

# TODO: Add some endpoint that traverses GroupIterations to collect solutions, preferences, etc.
@router.post("/all_iterations")
def full_iteration(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GNIMBUSAllIterationsResponse:

    group = session.exec(select(Group).where(Group.id == request.group_id)).first()
    if group is None:
        raise HTTPException(
            detail=f"No group with ID {request.group_id}!",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    if user.id not in group.user_ids:
        raise HTTPException(
            detail="Unauthorized user",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    groupiter = group.head_iteration.parent

    if groupiter is None:
        raise HTTPException(
            detail="Problem has not been initialized!",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    full_iterations: list[FullIteration] = []
    
    if groupiter.preferences.method == "optimization":
        # There are no full results because the latest iteration is optimization,
        # so add an incomplete entry to the list to be returned.
        prev_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.state_id)).first()
        if prev_state is None:
            raise HTTPException(
                detail="No state for starting results!",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        this_state = session.exec(select(StateDB).where(StateDB.id == groupiter.state_id)).first()
        if this_state is None:
            raise HTTPException(
                detail="No state in most recent iteration!",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        all_results = []
        for i, _ in enumerate(this_state.state.solver_results):
            all_results.append(SolutionReference(state=this_state, solution_index=i))

        full_iterations.append(
            FullIteration(
                phase=groupiter.preferences.phase,
                optimization_preferences=groupiter.preferences,
                voting_preferences=None,
                starting_result=SolutionReference(state=prev_state, solution_index=0),
                common_results=all_results[-4:],
                user_results=all_results[:-4],
                final_result=None,
            )
        )
        
        groupiter = groupiter.parent

    # We're at voting phase now.
    while groupiter is not None and groupiter.parent is not None and groupiter.parent.parent is not None:

        this_state = session.exec(select(StateDB).where(StateDB.id == groupiter.state_id)).first()
        prev_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.state_id)).first()
        first_state = session.exec(select(StateDB).where(StateDB.id == groupiter.parent.parent.state_id)).first()

        if this_state is None or prev_state is None or first_state is None:
            raise HTTPException(
                detail="Wääääää",
                status_code=status.HTTP_418_IM_A_TEAPOT
            )

        all_results = []
        for i, _ in enumerate(prev_state.state.solver_results):
            all_results.append(SolutionReference(state=prev_state, solution_index=i))

        full_iterations.append(
            FullIteration(
                phase=groupiter.parent.preferences.phase,
                optimization_preferences=groupiter.parent.preferences,
                voting_preferences=groupiter.preferences,
                starting_result=SolutionReference(state=first_state, solution_index=0),
                common_results=all_results[-4:],
                user_results=all_results[:-4],
                final_result=SolutionReference(state=this_state, solution_index=0)
            )
        )

        groupiter = groupiter.parent.parent
        

    response = GNIMBUSAllIterationsResponse(
        all_full_iterations=full_iterations
    )
    return response


@router.post("/toggle_phase")
def toggle_phase(
    request: GroupInfoRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)]
) -> JSONResponse:
    """Toggle the phase from learning to decision and vice versa"""
    
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

    iteration = group.head_iteration
    if iteration == None:
        raise HTTPException(
            detail="There's no iterations! Did you forget to initialize the problem?",
            status_code=status.HTTP_404_NOT_FOUND
        )
    if iteration.preferences == None:
        raise HTTPException(
            details="Now this is a funky problem!",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    if iteration.preferences.method == "voting":
        raise HTTPException(
            detail="You cannot switch the phase in the middle of the iteration.",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    old_phase = iteration.preferences.phase
    new_phase = "decision" if old_phase == "learning" else "learning"

    preferences: OptimizationPreference = copy.deepcopy(iteration.preferences)
    preferences.phase = new_phase

    iteration.preferences = preferences
    session.add(iteration)
    session.commit()
    session.refresh(iteration)

    return JSONResponse(
        content={
            "message": f"Phase switched from {old_phase} to {new_phase}.",
            "old_phase": old_phase,
            "new_phase": new_phase,
        },
        status_code=status.HTTP_200_OK
    )