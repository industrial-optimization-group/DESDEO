"""Db configuration loader."""

from desdeo.api.config import LoadDBConfig
from typing import Callable, List
from pydantic import ValidationError
from typing import Optional

class DbConfig:
    _host = None
    _port = None
    _database = None
    _username = None
    _password = None
    _pool_size = None
    _max_overflow = None
    _pool = None

    @classmethod
    def load_config(cls, settings: Optional[Callable[...,List[tuple]]] = None) -> "DbConfig":
        """Initialize configuration loading.

        Args:
            settings Optional[Callable[...,List[tuple]]]: configurations to overwrite global configs.

        Returns:
            DbConfig: DbConfig class object
        """"
        try:
            if settings:
                config = LoadDBConfig(**{key.lower():value for key,value in settings()})
            else:
                config = LoadDBConfig()

            cls._host = config.db_host
            cls._port = config.db_port
            cls._database = config.db_database
            cls._username = config.db_username
            cls._password = config.db_password
            cls._pool_size = config.db_pool_size
            cls._max_overflow = config.db_max_overflow
            cls._pool = config.db_pool
        except ValidationError:
            raise
        except Exception:
            raise TypeError("Config must be pydantic 'BaseSettings' or list of tuple")
