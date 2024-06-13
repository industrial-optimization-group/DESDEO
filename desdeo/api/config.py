"""Configuration file."""

from pydantic import (
    BaseModel,
    StrictStr,
    StrictInt,
    StrictBool
)
from typing import Optional, Union
from datetime import timedelta

class AuthConfig(BaseModel):
    """General configurations."""

    # openssl rand -hex 32
    authjwt_secret_key: Optional[StrictStr] = "36b96a23d24cebdeadce6d98fa53356111e6f3e85b8144d7273dcba230b9eb18"
    authjwt_algorithm: Optional[StrictStr] = "HS256"
    authjwt_access_token_expires: Optional[StrictInt] = 15 # in minutes
    authjwt_refresh_token_expires: Optional[StrictInt] = 30 # in minutes

class DBConfig(BaseModel):
    """Database configurations."""

    db_host: Optional[StrictStr] = "localhost"
    db_port: Optional[StrictStr] = "5432"
    db_database: Optional[StrictStr] = "DESDEO3"
    db_username: Optional[StrictStr] = "bhupindersaini"
    db_password: Optional[StrictStr] = ""
    db_pool_size: Optional[StrictInt] = 20
    db_max_overflow: Optional[StrictInt] = 20
    db_pool: Optional[StrictBool] = True