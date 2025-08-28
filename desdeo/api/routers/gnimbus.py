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
)
from desdeo.api.db import get_session
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.problem import Problem
from desdeo.mcdm.nimbus import generate_starting_point, solve_sub_problems
from desdeo.tools import SolverResults
from desdeo.tools.scalarization import ScalarizationError

from desdeo.api.routers.gdm_base import GroupManager
from desdeo.api.models.gnimbus import (
    GNIMBUSPreferenceResults,
    VotingPreferenceResults,
)

router = APIRouter(prefix="/gnimbus")

class GNIMBUSManager(GroupManager):

    async def gnimbus(
            self,
            user_id: int,
            data: str,
            session: Session,
            group: Group,
            current_iteration: GroupIteration,
    ) -> GNIMBUSPreferenceResults | None:
        """A function to handle the NIMBUS path"""

        # we know the type of data we need so we'll validate the data as ReferencePoint.
        try:
            preference = ReferencePoint.model_validate(json.loads(data))
        except ValidationError as e:
            await self.send_message(f"Unable to validate sent data as reference point: {e}", self.sockets[user_id])
            return None
        except json.decoder.JSONDecodeError as e:
            await self.send_message(f"Unable to decode data; make sure it is formatted properly.", self.sockets[user_id])
            return None
        except KeyError as e:
            await self.send_message(f"Unable to validate data; make sure it is formatted properly.", self.sockets[user_id])
            return None

        # Update the current GroupIteration's database entry with the new preferences
        # We need to do a deep copy here, otherwise the db entry won't be updated
        pref_results: GNIMBUSPreferenceResults = copy.deepcopy(current_iteration.pref_results)
        pref_results.set_preferences[user_id] = preference
        current_iteration.pref_results = pref_results
        session.add(current_iteration)
        session.commit()
        session.refresh(current_iteration)

        # Check if all preferences are in
        # There has to be a more elegant way of doing this
        pref_results: GNIMBUSPreferenceResults = current_iteration.pref_results
        for user_id in group.user_ids:
            try:
                # This shouldn't happen but just in case.
                if pref_results.set_preferences[user_id] == None:
                    logging.info("Not all prefs in!")
                    return None
            except KeyError:
                logging.info("Key error: Not all prefs in!")
                return None
        
        # If all preferences are in, begin optimization.
        problem_db: ProblemDB = session.exec(select(ProblemDB).where(ProblemDB.id == group.problem_id)).first()
        problem: Problem = Problem.from_problemdb(problem_db)
        prefs = current_iteration.pref_results.set_preferences

        # Here we choose only one preference as an example.
        # We could utilize some method specific synthetization methods.

        pref = prefs[group.user_ids[0]].aspiration_levels
        # And here we choose the first result of the previous iteration as the current objectives.
        # The previous solution could be perhaps voted, in a separate case of the surrounding match
        prev_sol = current_iteration.parent.pref_results.results[0].optimal_objectives
        
        # This is coming from nimbus
        try:
            results: list[SolverResults] = solve_sub_problems(
                problem,
                reference_point=pref,
                num_desired=4,
                current_objectives=prev_sol
            )
            logging.info(f"Optimization for group {self.group_id} done.")

        except ScalarizationError:
            await self.broadcast("Error while scalarizing: classifications must differ from previous iteration!")
            return None

        except Exception as e:
            await self.broadcast(f"An error occured while optimizing: {e}")
            return None
        
        # ADD optimization results into database
        pref_results = copy.deepcopy(current_iteration.pref_results)
        pref_results.results = results
        current_iteration.pref_results = pref_results
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

        # If we wanted to make a multi-phase voting type thing,
        # We would be returning a VotingPreferenceResult. Then the execution
        # would diverge to "Voting" branch.
        new_pref_results = GNIMBUSPreferenceResults(
            set_preferences={},
            results=[]
        )

        return new_pref_results
    
    async def voting(
        self,
        user_id: int,
        data: str,
        session: Session,
        group: Group,
        current_iteration: GroupIteration,
    ) -> VotingPreferenceResults | None:
        """ A function to handle voting path """

        # Here we would be creating a NIMBUSPreferenceResult
        # so it would be filled later on with ReferencePoints.
        return None


    async def optimize(
            self,
            user_id: int,
            data: str,
    ):
        """The optimization function.
        
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
            match current_iteration.pref_results.method:
                case "gnimbus":
                    new_pref_results = await self.gnimbus(
                        user_id=user_id,
                        data=data,
                        session=session,
                        group=group,
                        current_iteration=current_iteration
                    )

                case "voting":
                    # Here we could do some voting on the NIMBUS results.
                    new_pref_results = await self.voting(
                        user_id=user_id,
                        data=data,
                        session=session,
                        group=group,
                        current_iteration=current_iteration
                    )
                case _:
                    # throw an error or something
                    new_pref_results = None
                    return
            
            if new_pref_results == None:
                session.close()
                return
            
            # If everything has gone according to keikaku (keikaku means plan), create the next iteration.
            next_iteration = GroupIteration(
                group_id=self.group_id,
                group=group,
                problem_id=current_iteration.problem_id,
                pref_results=new_pref_results,
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
    start_iteration = GroupIteration(
        problem_id=group.problem_id,
        group_id=group.id,
        group=group,
        pref_results=GNIMBUSPreferenceResults(
            set_preferences={},
            results=[generate_starting_point(problem)]
        ),
        notified={},
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
        pref_results=GNIMBUSPreferenceResults(
            set_preferences={},
            results=[],
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
    
    if iteration.pref_results.results == None:
        raise nores_exp

    return JSONResponse(
        content={
            "results": [result.model_dump()["optimal_objectives"] for result in iteration.pref_results.results]
        },
        status_code=status.HTTP_200_OK
    )