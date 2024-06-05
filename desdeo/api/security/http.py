from pydantic import BaseModel
from typing_extensions import Annotated, Doc
from fastapi.param_functions import Form

class InviteForm:
    def __init__(
        self,
        *,
        invitee: Annotated[
            int,
            Form(),
            Doc(
                """
                `invitee` string.
                """
            ),
        ],
        problem_id: Annotated[
            int,
            Form(),
            Doc(
                """
                `problem_id` int.
                """
            ),
        ],
    ):
        self.invitee = invitee
        self.problem_id = problem_id
