"""Defines dataclasses to store configurations loaded from 'config.toml'."""

import tomllib
import os
import json
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel

# Load the config data once
config_path = Path(__file__).resolve().parent / "config.toml"
with config_path.open("rb") as fp:
    config_data = tomllib.load(fp)


class SettingsConfig(BaseModel):
    """General settings."""

    # If DESDEO_PRODUCTION env variable is something resembling true, then do not use the debug value from config
    debug: ClassVar[bool] = (
        False
        if os.getenv("DESDEO_PRODUCTION", "").strip().lower() in ("1", "true", "yes", "on")
        else config_data["settings"]["debug"]
    )


class ServerDebugConfig(BaseModel):
    """Server setup settings (development)."""

    test_user_analyst_name: ClassVar[str] = config_data["server-debug"]["test_user_analyst_name"]
    test_user_analyst_password: ClassVar[str] = config_data["server-debug"]["test_user_analyst_password"]
    test_user_dm1_name: ClassVar[str] = config_data["server-debug"]["test_user_dm1_name"]
    test_user_dm1_password: ClassVar[str] = config_data["server-debug"]["test_user_dm1_password"]
    test_user_dm2_name: ClassVar[str] = config_data["server-debug"]["test_user_dm2_name"]
    test_user_dm2_password: ClassVar[str] = config_data["server-debug"]["test_user_dm2_password"]


class AuthDebugConfig(BaseModel):
    """Authentication settings (development)."""

    authjwt_secret_key: ClassVar[str] = config_data["auth-debug"]["authjwt_secret_key"]
    authjwt_algorithm: ClassVar[str] = config_data["auth-debug"]["authjwt_algorithm"]
    authjwt_access_token_expires: ClassVar[int] = config_data["auth-debug"]["authjwt_access_token_expires"]
    authjwt_refresh_token_expires: ClassVar[int] = config_data["auth-debug"]["authjwt_refresh_token_expires"]
    cors_origins: ClassVar[list[str]] = config_data["auth-debug"]["cors_origins"]
    cookie_domain: ClassVar[str] = config_data["auth-debug"]["cookie_domain"]


class DatabaseDebugConfig(BaseModel):
    """Database setting (development)."""

    db_host: ClassVar[str] = config_data["database-debug"]["db_host"]
    db_port: ClassVar[str] = config_data["database-debug"]["db_port"]
    db_database: ClassVar[str] = config_data["database-debug"]["db_database"]
    db_username: ClassVar[str] = config_data["database-debug"]["db_username"]
    db_password: ClassVar[str] = config_data["database-debug"]["db_password"]
    db_pool_size: ClassVar[int] = config_data["database-debug"]["db_pool_size"]
    db_max_overflow: ClassVar[int] = config_data["database-debug"]["db_max_overflow"]
    db_pool: ClassVar[bool] = config_data["database-debug"]["db_pool"]


class DatabaseDeployConfig(BaseModel):
    """Database setting (deployment)."""

    db_host: str = os.getenv("DB_HOST")
    db_port: str = os.getenv("DB_PORT")
    db_database: str = os.getenv("DB_NAME")
    db_username: str = os.getenv("DB_USER")
    db_password: str = os.getenv("DB_PASSWORD")
    db_pool_size: int = config_data["database-deploy"]["db_pool_size"]
    db_max_overflow: int = config_data["database-deploy"]["db_max_overflow"]
    db_pool: bool = config_data["database-deploy"]["db_pool"]
    db_driver: str = os.getenv("DB_DRIVER", config_data["database-deploy"]["db_driver"])


class AuthDeployConfig(BaseModel):
    authjwt_secret_key: ClassVar[str] = os.getenv("AUTHJWT_SECRET")
    authjwt_algorithm: str = config_data["auth-deploy"]["authjwt_algorithm"]
    authjwt_access_token_expires: int = config_data["auth-deploy"]["authjwt_access_token_expires"]
    authjwt_refresh_token_expires: int = config_data["auth-deploy"]["authjwt_refresh_token_expires"]
    cors_origins: ClassVar[list[str]] = (
        json.loads(os.getenv("CORS_ORIGINS"))
        if os.environ.get("CORS_ORIGINS") is not None
        else config_data["auth-debug"]["cors_origins"]
    )
    cookie_domain: ClassVar[str] = os.getenv("COOKIE_DOMAIN", "")
