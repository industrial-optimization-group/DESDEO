import time
from typing import Annotated
from hashlib import blake2b

from fastapi import APIRouter, Depends

from desdeo.api.db_models import Invite
from desdeo.api.schema import User
from desdeo.api.routers.UserAuth import get_current_user
from desdeo.api.security.http import InviteForm
from desdeo.api.utils.database import (
    database_dependency,
)

router = APIRouter()

def create_invite_code(data: dict) -> str:
    data = data.copy()
    code = blake2b(str.encode(str(data)), digest_size=8).hexdigest() + str(time.time())
    return code

@router.post("/invite")
async def createInvite(
    form_data: Annotated[InviteForm, Depends()],
    db: Annotated[database_dependency, Depends()],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    code = create_invite_code({"invitee": form_data.invitee, "problem_id": form_data.problem_id})
    new_invite = Invite(
        inviter = user.index,
        invitee = form_data.invitee,
        problem_id = form_data.problem_id,
        code = code
    )

    await db.add(new_invite)
    await db.commit()

    return { "code": code }

