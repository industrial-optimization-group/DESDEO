from pydantic import (
    BaseModel,
    StrictStr,
    StrictInt
)
from typing import Optional, Union
from datetime import timedelta

class LoadConfig(BaseModel):
    # openssl rand -hex 32
    authjwt_secret_key: Optional[StrictStr] = "36b96a23d24cebdeadce6d98fa53356111e6f3e85b8144d7273dcba230b9eb18"
    authjwt_algorithm: Optional[StrictStr] = "HS256"
    authjwt_access_token_expires: Optional[StrictInt] = 15 # in minutes
    authjwt_refresh_token_expires: Optional[StrictInt] = 30 # in minutes