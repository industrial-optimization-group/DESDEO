"""Router for evolutionary multiobjective optimization (EMO) methods."""

import json
from asyncio import run
from collections.abc import Callable
from datetime import datetime
from multiprocessing import Manager as ProcessManager
from multiprocessing import Process
from multiprocessing.synchronize import Event as EventClass  # only for typing, can be removed
from pathlib import Path
from typing import Annotated
from warnings import warn

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlmodel import select
from websockets.asyncio.client import connect

from desdeo.api.db import get_session
from desdeo.api.models import StateDB
from desdeo.api.models.emo import (
    EMOFetchRequest,
    EMOIterateRequest,
    EMOIterateResponse,
    EMOScoreRequest,
    EMOScoreResponse,
)
from desdeo.api.models.state import EMOIterateState, EMOSCOREState
from desdeo.emo.options.templates import EMOOptions, PreferenceOptions, TemplateOptions, emo_constructor
from desdeo.problem import Problem
from desdeo.tools.score_bands import SCOREBandsConfig, score_json

from .utils import SessionContext, get_session_context

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
        self.unsent_messages: dict[str, list[dict]] = {}
        """A dictionary to store unsent messages for clients that are not currently connected."""

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        if client_id in self.unsent_messages:
            for message in self.unsent_messages[client_id]:
                await websocket.send_json(message)
            self.unsent_messages.pop(client_id, None)

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
            if client_id not in self.unsent_messages:
                self.unsent_messages[client_id] = []
            self.unsent_messages[client_id].append(message)
            warn(
                f"Client with id={client_id} is not connected. Message saved, will be sent upon connection.",
                stacklevel=2,
            )

    async def broadcast_message(self, message: dict):
        """Sends a message to all active WebSocket connections.

        Typically don't use this as this won't send messages
        to disconnected/unconnected clients.
        """
        for websocket in self.active_connections.values():
            await websocket.send_json(message)


ws_manager = WSmanager()


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


async def handle_stop_event(stop_event: EventClass, listener_id: str):
    """Handles the stop event for the WebSocket connections."""
    async with connect(f"ws://localhost:8000/method/emo/ws/{listener_id}") as websocket:
        while True:
            data = await websocket.receive_json()
            if "message" in data and data["message"] == "stop":
                stop_event.set()
                break


def get_templates() -> list[TemplateOptions]:
    """Fetches available EMO templates."""
    current_dir = Path(__file__)
    # Should be a database lookup in the future
    json_load_path = current_dir.parent.parent.parent.parent / "datasets" / "emoTemplates"

    algos = ["nsga3"]

    templates = []
    for algo in algos:
        with Path.open(json_load_path / f"{algo}.json", "r") as f:
            data = json.load(f)
            template = EMOOptions.model_validate(data)
            templates.append(template.template)
    return templates


@router.post("/iterate")
def iterate(
    request: EMOIterateRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> EMOIterateResponse:
    """Fetches results from a completed EMO method.

    Args: request (EMOIterateRequest): The request object containing parameters for fetching results.
        context (Annotated[SessionContext, Depends]): The session context.
    """
    # 1) Get context objects
    db_session = context.db_session
    interactive_session = context.interactive_session
    parent_state = context.parent_state

    # 2) Ensure problem exists
    if context.problem_db is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    problem_db = context.problem_db
    problem = Problem.from_problemdb(problem_db)

    # 3) Templates
    templates = request.template_options or get_templates()

    web_socket_ids = [
        f"{template.algorithm_name.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}" for template in templates
    ]

    client_id = f"client_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    # 4) Create incomplete state
    emo_iterate_state = EMOIterateState(
        template_options=jsonable_encoder(templates),
        preference_options=jsonable_encoder(request.preference_options),
    )

    incomplete_db_state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=interactive_session.id if interactive_session else None,
        parent_id=parent_state.id if parent_state else None,
        state=emo_iterate_state,
    )

    db_session.add(incomplete_db_state)
    db_session.commit()
    db_session.refresh(incomplete_db_state)

    state_id = incomplete_db_state.id
    if state_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create a new state in the database.",
        )

    # 5) Start process
    Process(
        target=_spawn_emo_process,
        args=(
            problem,
            templates,
            request.preference_options,
            web_socket_ids,
            client_id,
            state_id,
        ),
    ).start()

    return EMOIterateResponse(method_ids=web_socket_ids, client_id=client_id, state_id=state_id)


def _spawn_emo_process(
    problem: Problem,
    templates: list[TemplateOptions],
    preference_options: PreferenceOptions | None,
    websocket_ids: list[str],
    client_id: str,
    state_id: int,
):
    """Spawns a new process to handle the EMO method.

    In turn, this will start multiple processes for each evolutionary algorithm.
    It will collect results and update the database.

    Args:
        problem (Problem): The problem object.
        templates (List[TemplateOptions]): The list of templates to use.
        preference_options (PreferenceOptions | None): The preference options to use.
        websocket_ids (list[str]): The list of WebSocket IDs.
        client_id (str): The client ID for WebSocket communication.
        state_id (int): The state ID in the database to update with results.
    """
    process_manager = ProcessManager()
    stop_event = process_manager.Event()
    results_dict = process_manager.dict()
    # Spawn a bunch of EAs
    processes = []

    for w_id, template in zip(
        websocket_ids, templates, strict=True
    ):  # Skip the first id, which is for the webui client
        p = Process(
            target=_ea_sync,
            args=(problem, template, preference_options, stop_event.is_set, w_id, client_id, results_dict),
        )
        processes.append(p)
        p.start()

    # collect results
    for p in processes:
        p.join()

    # Combine results
    optimal_variables = pl.concat([results.optimal_variables for results in results_dict.values()])
    optimal_outputs = pl.concat([results.optimal_outputs for results in results_dict.values()])
    # update DB
    session = next(get_session())
    statement = select(StateDB).where(StateDB.id == state_id)
    state = session.exec(statement).first()
    if state is None:
        raise ValueError(f"Could not find state with id={state_id} to update with results.")
    emo_state = state.state
    if not isinstance(emo_state, EMOIterateState):
        raise TypeError(f"State with id={state_id} is not of type EMOIterateState.")
    # TODO(@light-weaver): Just a dirty way to handle this. Use non-dominated merge and also split dec and obj vars
    var_names = [var.symbol for var in problem.get_flattened_variables()]
    obj_names = [obj.symbol for obj in problem.objectives]
    if problem.constraints is not None:  # noqa: SIM108
        constr_names = [constr.symbol for constr in problem.constraints]
    else:
        constr_names = []
    if problem.extra_funcs is not None:  # noqa: SIM108
        extra_names = [extra.symbol for extra in problem.extra_funcs]
    else:
        extra_names = []

    emo_state.decision_variables = optimal_variables[var_names].to_dict(as_series=False)
    emo_state.objective_values = optimal_outputs[obj_names].to_dict(as_series=False)
    emo_state.constraint_values = optimal_outputs[constr_names].to_dict(as_series=False) if constr_names else None
    emo_state.extra_func_values = optimal_outputs[extra_names].to_dict(as_series=False) if extra_names else None

    session.add(emo_state)
    session.commit()
    session.close()


def _ea_sync(
    problem: Problem,
    template: TemplateOptions,
    preference_options: PreferenceOptions | None,
    stop_event: Callable[[], bool],
    websocket_id: str,
    client_id: str,
    results_dict: dict,
):
    """Synchronous wrapper to run the evolutionary algorithm in an async event loop.

    Args:
        problem (Problem): The problem object.
        template (TemplateOptions): The template options for the EMO method.
        preference_options (PreferenceOptions | None): The preference options for the EMO method.
        stop_event (Callable[[], bool]): A callable that returns True if the algorithm should stop.
        websocket_id (str): The WebSocket ID for the current EMO method for communication.
        client_id (str): The ID of the client to send websocket messages to.
        results_dict (dict): A shared ProcessManager dictionary to store results.
    """
    run(
        _ea_async(
            problem=problem,
            websocket_id=websocket_id,
            client_id=client_id,
            stop_event=stop_event,
            results_dict=results_dict,
            template=template,
            preference_options=preference_options,
        )
    )


async def _ea_async(
    problem: Problem,
    websocket_id: str,
    client_id: str,
    stop_event: Callable[[], bool],
    results_dict: dict,
    template: TemplateOptions,
    preference_options: PreferenceOptions | None = None,
):
    """Executes an evolutionary algorithm.

    Args:
        problem (Problem): The problem object.
        websocket_id (str): The WebSocket ID for the current EMO method for communication.
        client_id (str): The ID of the client to send websocket messages to.
        stop_event (Event): The stop event to signal when to stop the algorithm.
        results_dict (dict): A shared ProcessManager dictionary to store results.
        template (TemplateOptions): The template options for the EMO method.
        preference_options (PreferenceOptions | None): The preference options for the EMO method.
    """
    # TODO: the url should not be hardcoded
    async with connect(f"ws://localhost:8000/method/emo/ws/{websocket_id}") as ws:
        text = f'{{"message": "Started {websocket_id}", "send_to": "{client_id}"}}'
        await ws.send(text)
        emo_options = EMOOptions(template=template, preference=preference_options)
        solver, extras = emo_constructor(emo_options, problem=problem, external_check=stop_event)
        results = solver()
        if extras.archive is not None:
            results = extras.archive.results
        await ws.send(f'{{"message": "Finished {websocket_id}", "send_to": "{client_id}"}}')
        results_dict[websocket_id] = results


@router.post("/fetch")
async def fetch_results(
    request: EMOFetchRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> StreamingResponse:
    """Fetches results from a completed EMO method.

    Args:
        request (EMOFetchRequest): The request object containing parameters for fetching results.
        context (Annotated[SessionContext, Depends]): The session context.

    Raises: HTTPException: If the request is invalid or the EMO method has not completed.

    Returns: StreamingResponse: A streaming response containing the results of the EMO method.
    """
    # Use context instead of manual fetch
    state = context.parent_state

    if state is None:
        raise HTTPException(status_code=404, detail="Parent state not found.")

    if not isinstance(state.state, EMOIterateState):
        raise TypeError(f"State with id={request.parent_state_id} is not of type EMOIterateState.")

    if not (state.state.objective_values and state.state.decision_variables):
        raise ValueError("State does not contain results yet.")

    # Convert objs: dict[str, list[float]] to objs: list[dict[str, float]]
    raw_objs: dict[str, list[float]] = state.state.objective_values
    n_solutions = len(next(iter(raw_objs.values())))
    objs: list[dict[str, float]] = [{k: v[i] for k, v in raw_objs.items()} for i in range(n_solutions)]

    raw_decs: dict[str, list[float]] = state.state.decision_variables
    decs: list[dict[str, float]] = [{k: v[i] for k, v in raw_decs.items()} for i in range(n_solutions)]

    def result_stream():
        for i in range(n_solutions):
            item = {
                "solution_id": i,
                "objective_values": objs[i],
                "decision_variables": decs[i],
            }
            yield json.dumps(item) + "\n"

    return StreamingResponse(result_stream())


@router.post("/fetch_score")
async def fetch_score_bands(
    request: EMOScoreRequest,
    context: Annotated[SessionContext, Depends(get_session_context)],
) -> EMOScoreResponse:
    """Fetches results from a completed EMO method.

    Args: request (EMOFetchRequest): The request object containing parameters for fetching
        results and of the SCORE bands visualization.
        context (Annotated[SessionContext, Depends]): The session context.

    Raises:
        HTTPException: If the request is invalid or the EMO method has not completed.

    Returns:
        SCOREBandsResult: The results of the SCORE bands visualization.
    """
    # Use context instead of manual fetch
    parent_state = context.parent_state
    db_session = context.db_session
    problem_db = context.problem_db

    if parent_state is None:
        raise HTTPException(status_code=404, detail="Parent state not found.")

    if not isinstance(parent_state.state, EMOIterateState):
        raise TypeError(f"State with id={request.parent_state_id} is not of type EMOIterateState.")

    if not (parent_state.state.objective_values and parent_state.state.decision_variables):
        raise ValueError("State does not contain results yet.")

    score_config = SCOREBandsConfig() if request.config is None else request.config

    raw_objs: dict[str, list[float]] = parent_state.state.objective_values
    objs = pl.DataFrame(raw_objs)

    results = score_json(
        data=objs,
        options=score_config,
    )

    score_state = EMOSCOREState(result=results.model_dump())

    # Use the session + problem from context instead of request directly
    score_db_state = StateDB.create(
        database_session=db_session,
        problem_id=problem_db.id,
        session_id=parent_state.session_id,
        parent_id=parent_state.id,
        state=score_state,
    )

    db_session.add(score_db_state)
    db_session.commit()
    db_session.refresh(score_db_state)

    state_id = score_db_state.id

    return EMOScoreResponse(result=results, state_id=state_id)
