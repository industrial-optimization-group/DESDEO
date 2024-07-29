from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field,  Extra

from desdeo.api.db_models import MethodState
from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.schema import User

from desdeo.api.utils.database import (
    database_dependency,
    select,
    DB,
)

from .GNIMBUS import (
    NIMBUSIterateRequest,
    ChooseRequest,
    VoteRequest,
    FinalVoteRequest,
)

router = APIRouter(prefix="/gmethod")

class Request(BaseModel, extra=Extra.allow):
    method: str = Field(description="Method name.")
    request_type: str = Field(description="Type of the request.")

REQUEST_MODELS = {
    "nimbus": {
        "iterate": NIMBUSIterateRequest,
        "choose": ChooseRequest,
        "vote": VoteRequest,
        "vote_as_final": FinalVoteRequest,
    }
}

@router.post("/save-request")
async def save_request(
    requestToSave: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DB, Depends(database_dependency)],
) -> dict:
    """Save request.

    Args:
        requestToSave (SingleNavigateRequestRequest): The request to be saved.
        user (Annotated[User, Depends(get_current_user)]): The current user.
        db (Annotated[DB, Depends(database_dependency)]): The database session.

    Returns:
        dict: Information about the saved request.
    """

    requestModel = REQUEST_MODELS[requestToSave.method][requestToSave.request_type]
    request = requestModel(**requestToSave.dict())

    row = MethodState(
        user=user.index,
        problem=request.problem_id,
        value=request.model_dump(mode="json")
    )

    await db.add(row)
    await db.commit()

    return { "id": row.id }