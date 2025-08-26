"""Router for evolutionary multiobjective optimization (EMO) methods."""

from asyncio import run
from datetime import datetime
from multiprocessing import Manager as ProcessManager
from multiprocessing import Process
from multiprocessing.synchronize import Event as EventClass  # only for typing, can be removed
from typing import Annotated, Dict, List, Optional
from warnings import warn

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlmodel import select
from websockets.client import connect

from desdeo.api.db import get_session
from desdeo.api.models.EMO import (
    EMOSolveRequest,
)
from desdeo.api.models.preference import (
    NonPreferredSolutions,
    PreferenceBase,
    PreferenceDB,
    PreferredRanges,
    PreferredSolutions,
    ReferencePoint,
)
from desdeo.api.models.problem import ProblemDB
from desdeo.api.models.state import EMOSaveState, EMOState, StateDB
from desdeo.api.models.user import User
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.utils.database import user_save_solutions
from desdeo.api.utils.emo_database import _convert_dataframe_to_dict_list
from desdeo.emo.hooks.archivers import NonDominatedArchive
from desdeo.emo.methods.EAs import nsga3, rvea
from desdeo.problem import Problem

router = APIRouter(prefix="/method/emo", tags=["EMO"])


class WSmanager:
    """Manages active WebSocket connections for EMO methods."""

    def __init__(self):
        """Initializes the WebSocket manager."""
        self.active_connections: dict[str, WebSocket] = {}
        """
        A dictionary to keep track of active WebSocket connections.
        The keys are the client identifiers. Note: not the same as `websocket.client`,
        which is just a tuple of (host, port). Nor is it the user id. Each new
        EA instance will have its own unique identifier. The webui client should
        get its id from the server.
        """

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, websocket: WebSocket):
        """Removes a WebSocket connection."""
        for client_id, ws in self.active_connections.items():
            if ws.client == websocket.client:
                client_id_to_remove = client_id
        self.active_connections.pop(client_id_to_remove, None)

    async def send_private_message(self, message: dict, client_id: str):
        """Sends a private message to a specific WebSocket connection."""
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_json(message)
        else:
            raise ValueError(f"No active connection for client_id: {client_id}")

    async def broadcast_message(self, message: dict):
        """Sends a message to all active WebSocket connections."""
        for websocket in self.active_connections.values():
            await websocket.send_json(message)


ws_manager = WSmanager()


async def handle_stop_event(stop_event: EventClass, listener_id: str):
    """Handles the stop event for the WebSocket connections."""
    with connect(f"ws://localhost:8000/method/emo/ws/{listener_id}") as websocket:
        while True:
            data = await websocket.receive_json()
            if "message" in data and data["message"] == "stop":
                stop_event.set()
                break


class IterateResponse(BaseModel):
    ws_ids: list[str]
    current_state_id: int


@router.post("/iterate")
def iterate(
    request: EMOSolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> IterateResponse:
    """Starts the EMO method.

    Args:
        request (EMOSolveRequest): The request object containing parameters for the EMO method.
        user (Annotated[User, Depends]): The current user.
        session (Annotated[Session, Depends]): The database session.

    Raises:
        HTTPException: If the request is invalid or the EMO method fails.

    Returns:
        IterateResponse: A response object containing a list of IDs to be used for websocket communication.
            Also contains the StateDB id where the results will be stored.
    """
    # Fetch problem from DB
    statement = select(ProblemDB).where(ProblemDB.user_id == user.id, ProblemDB.id == request.problem_id)
    problem_db = session.exec(statement).first()

    if problem_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with id={request.problem_id} could not be found.",
        )

    # Convert ProblemDB to Problem object
    problem = Problem.from_problemdb(problem_db)

    ws_ids = ["client", "rvea", "nsga3"]
    # Save request (incomplete and EAs have not finished running yet)

    # Create DB preference
    preference_db = PreferenceDB(user_id=user.id, problem_id=problem_db.id, preference=request.preference)

    session.add(preference_db)
    session.commit()
    session.refresh(preference_db)

    # Handle parent state
    if request.parent_state_id is None:
        parent_state = None
    else:
        statement = select(StateDB).where(StateDB.id == request.parent_state_id)
        parent_state = session.exec(statement).first()

        if parent_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find state with id={request.parent_state_id}",
            )

    incomplete_emo_state = EMOState(
        method=request.method,  # Use the method directly (already uppercase)
        max_evaluations=request.max_evaluations,
        number_of_vectors=request.number_of_vectors,
        use_archive=request.use_archive,
        solutions=[],
        outputs=[],
    )

    incomplete_db_state = StateDB(
        problem_id=problem_db.id,
        preference_id=preference_db.id,
        session_id=None,
        parent_id=parent_state.id if parent_state is not None else None,
        state=incomplete_emo_state,  # Convert to dict for JSON serialization
    )

    session.add(incomplete_db_state)
    session.commit()
    session.refresh(incomplete_db_state)

    state_id = incomplete_db_state.id

    # Close db session
    session.close()

    # Spawn a new process to handle EMO method creation
    Process(target=spawn_emo_process, args=(problem, ws_ids, state_id)).start()

    return IterateResponse(ws_ids=ws_ids, current_state_id=state_id)


def spawn_emo_process(
    problem: Problem,
    ws_ids: list[str],
    state_id: int,
):
    """Spawns a new process to handle the EMO method.

    In turn, this will start multiple processes for each evolutionary algorithm.
    It will collect results and update the database.

    Args:
        problem (Problem): The problem object.
        ws_ids (list[str]): The list of WebSocket IDs.
    """
    process_manager = ProcessManager()
    stop_event = process_manager.Event()
    results_dict = process_manager.dict()
    # Spawn a bunch of EAs
    processes = []
    for ea_name in ws_ids[1:]:  # Skip the first id, which is for the webui client
        p = Process(target=ea_sync, args=(problem, ea_name, stop_event, results_dict))
        processes.append(p)
        p.start()

    # collect results
    for p in processes:
        p.join()

    import polars as pl

    # Combine results
    combined_results = pl.concat([pl.DataFrame(results) for results in results_dict.values()])
    # update DB
    session = next(get_session())
    statement = select(StateDB).where(StateDB.id == state_id)
    state = session.exec(statement).first()
    emo_state = state.state
    # TODO(@light-weaver): Just a dirty way to handle this. Use non-dominated merge and also split dec and obj vars
    emo_state.solutions = combined_results.to_dict(as_series=False)
    emo_state.outputs = combined_results.to_dict(as_series=False)
    state.state = EMOState(
        method=emo_state.method,
        max_evaluations=emo_state.max_evaluations,
        number_of_vectors=emo_state.number_of_vectors,
        use_archive=emo_state.use_archive,
        solutions=[combined_results.to_dict(as_series=False)],
        outputs=[combined_results.to_dict(as_series=False)],
    )
    session.add(state)
    session.commit()
    session.close()


def ea_sync(problem: Problem, ea_name, stop_event, results_dict):
    run(ea_async(problem, ea_name, stop_event, results_dict))


async def ea_async(problem: Problem, ea_name, stop_event, results_dict):
    """Executes an evolutionary algorithm.

    Args:
        problem (Problem): The problem object.
        ea_name (str): The name of the evolutionary algorithm.
        stop_event (Event): The stop event to signal when to stop the algorithm.
    """
    async with connect(f"ws://localhost:8000/method/emo/ws/{ea_name}") as ws:
        text = f'{{"message": "Started {ea_name}", "send_to": "client"}}'
        await ws.send(text)
        solvers = {"rvea": rvea, "nsga3": nsga3}
        solver, publisher = solvers[ea_name](problem=problem)
        archiver = NonDominatedArchive(problem=problem, publisher=publisher)
        publisher.auto_subscribe(archiver)
        _ = solver()
        await ws.send(f'{{"message": "Finished {ea_name}", "send_to": "client"}}')
        results_dict[ea_name] = archiver.solutions.to_dict(as_series=False)


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    # TODO(@light-weaver): Add authentication
):
    """WebSocket endpoint for EMO methods."""
    await ws_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if "send_to" in data:
                try:
                    await ws_manager.send_private_message(data, data["send_to"])
                except ValueError as e:
                    warn(f"ValueError in WebSocket communication: {e}", stacklevel=2)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
