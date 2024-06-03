from desdeo.api.config import LoadConfig
from typing import Callable, List
from pydantic import ValidationError
from typing import Optional

class AuthConfig:
    _secret_key = None
    _algorithm = None
    _access_token_expires = None
    _refresh_token_expires = None

    @classmethod
    def load_config(cls, settings: Optional[Callable[...,List[tuple]]] = None) -> "AuthConfig":
        try:
            if settings:
                config = LoadConfig(**{key.lower():value for key,value in settings()})
            else:
                config = LoadConfig()

            cls._secret_key = config.authjwt_secret_key
            cls._algorithm = config.authjwt_algorithm
            cls._access_token_expires = config.authjwt_access_token_expires
            cls._refresh_token_expires = config.authjwt_refresh_token_expires
        except ValidationError:
            raise
        except Exception:
            raise TypeError("Config must be pydantic 'BaseSettings' or list of tuple")
