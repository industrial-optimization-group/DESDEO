from pydantic import BaseModel
from typing_extensions import Annotated, Doc
from fastapi.param_functions import Form

class InviteForm:
    """
        This is a dependency class to collect the `user_id` and `problem_id` as form data
        for an invitation.
    """

    def __init__(
        self,
        *,
        invitee: Annotated[
            int,
            Form(),
            Doc(
                """
                `invitee` int. The InviteForm requires the exact field name
                `invitee`.
                """
            ),
        ],
        problem_id: Annotated[
            int,
            Form(),
            Doc(
                """
                `problem_id` int. The InviteForm spec requires the exact field name
                `problem_id`.
                """
            ),
        ],
    ):
        self.invitee = invitee
        self.problem_id = problem_id

