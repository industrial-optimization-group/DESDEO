from typing_extensions import Annotated, Doc
from fastapi.param_functions import Form

class HTTPTokenCredentials:
    def __init__(
        self,

        code: Annotated[
            str,
            Form(),
            Doc(
                """
                `code` string. The HTTP spec requires the exact field name
                `code`.
                """
            ),
        ],

    ):
        self.code = code
