"""Configuration file."""
import os
import json

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

    db_host: ClassVar[StrictStr] = os.getenv("POSTGRES_HOST") or "localhost"
    db_port: ClassVar[StrictStr] = os.getenv("POSTGRES_PORT") or "5432"
    db_database: ClassVar[StrictStr] = os.getenv("POSTGRES_DB") or "test"
    db_username: ClassVar[StrictStr] = os.getenv("POSTGRES_USER") or "test"
    db_password: ClassVar[StrictStr] = os.getenv("POSTGRES_PASSWORD") or "testpw"
    db_pool_size: ClassVar[StrictInt] = int(os.getenv("POSTGRES_POOLSIZE") or 20)
    db_max_overflow: ClassVar[StrictInt] = int(os.getenv("POSTGRES_OVERFLOW") or 20)
    db_pool: ClassVar[StrictBool] = (os.getenv("POSTGRES_POOL") or True) in (True, 'true', '1', 't', 'y', 'yes')

class WebUIConfig(BaseModel):
    """Webui server configurations."""
    # Below defaults to ["http://localhost", "http://localhost:8080"] if no env variable is set
    cors_origins: ClassVar[list] = json.loads(os.getenv("CORS_ORIGINS",'["http://localhost", "http://localhost:8080"]'))