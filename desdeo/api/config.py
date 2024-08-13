"""Configuration file."""

from pydantic import (
    BaseModel,
    StrictStr,
    StrictInt,
    StrictBool
)
from typing import ClassVar, Optional, Union
from datetime import timedelta

class AuthConfig(BaseModel):
    """General configurations."""

    # openssl rand -hex 32
    authjwt_secret_key: ClassVar[StrictStr] = "36b96a23d24cebdeadce6d98fa53356111e6f3e85b8144d7273dcba230b9eb18"
    authjwt_algorithm: ClassVar[StrictStr] = "HS256"
    authjwt_access_token_expires: ClassVar[StrictInt] = 15 # in minutes
    authjwt_refresh_token_expires: ClassVar[StrictInt] = 30 # in minutes

class DBConfig(BaseModel):
    """Database configurations."""

    db_host: ClassVar[StrictStr] = "86.50.253.131"
    db_port: ClassVar[StrictStr] = "5432"
    db_database: ClassVar[StrictStr] = "test"
    db_username: ClassVar[StrictStr] = "test"
    db_password: ClassVar[StrictStr] = "testdb"
    db_pool_size: ClassVar[StrictInt] = 20
    db_max_overflow: ClassVar[StrictInt] = 20
    db_pool: ClassVar[StrictBool] = True