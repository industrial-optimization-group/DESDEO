"""Defines dataclasses to store configurations loaded from 'config.toml'."""

import tomllib
import os
import json
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Load the config data once
config_path = Path(__file__).resolve().parent / "config.toml"
with config_path.open("rb") as fp:
    config_data = tomllib.load(fp)


class GeneralSettings(BaseSettings):
    """General settings."""

    debug: bool = config_data["settings"]["debug"]


SettingsConfig = GeneralSettings()


class ServerDebugConfig(BaseSettings):
    """Server setup settings (development)."""

    test_user_analyst_name: str = config_data["server-debug"]["test_user_analyst_name"]
    test_user_analyst_password: str = config_data["server-debug"]["test_user_analyst_password"]
    test_user_dm1_name: str = config_data["server-debug"]["test_user_dm1_name"]
    test_user_dm1_password: str = config_data["server-debug"]["test_user_dm1_password"]
    test_user_dm2_name: str = config_data["server-debug"]["test_user_dm2_name"]
    test_user_dm2_password: str = config_data["server-debug"]["test_user_dm2_password"]


class AuthDebugConfig(BaseSettings):
    """Authentication settings (debug)."""

    authjwt_secret_key: str = config_data["auth-debug"]["authjwt_secret_key"]
    authjwt_algorithm: str = config_data["auth-debug"]["authjwt_algorithm"]
    authjwt_access_token_expires: int = config_data["auth-debug"]["authjwt_access_token_expires"]
    authjwt_refresh_token_expires: int = config_data["auth-debug"]["authjwt_refresh_token_expires"]
    cors_origins: List[str] = config_data["auth-debug"]["cors_origins"]
    cookie_domain: str = config_data["auth-debug"]["cookie_domain"]


class DatabaseDebugConfig(BaseSettings):
    """Database setting (development)."""

    db_host: str = config_data["database-debug"]["db_host"]
    db_port: str = config_data["database-debug"]["db_port"]
    db_database: str = config_data["database-debug"]["db_database"]
    db_username: str = config_data["database-debug"]["db_username"]
    db_password: str = config_data["database-debug"]["db_password"]
    db_pool_size: int = config_data["database-debug"]["db_pool_size"]
    db_max_overflow: int = config_data["database-debug"]["db_max_overflow"]
    db_pool: bool = config_data["database-debug"]["db_pool"]


class DatabaseDeployConfig(BaseSettings):
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


class AuthDeployConfig(BaseSettings):
    """Authentication settings (deployment)."""

    authjwt_secret_key: str = os.getenv("AUTHJWT_SECRET")
    authjwt_algorithm: str = config_data["auth-deploy"]["authjwt_algorithm"]
    authjwt_access_token_expires: int = config_data["auth-deploy"]["authjwt_access_token_expires"]
    authjwt_refresh_token_expires: int = config_data["auth-deploy"]["authjwt_refresh_token_expires"]
    cors_origins: List[str] = json.loads(os.getenv("CORS_ORIGINS", "[]"))
    cookie_domain: str = os.getenv("COOKIE_DOMAIN", "")


AuthConfig = AuthDebugConfig() if SettingsConfig.debug else AuthDeployConfig()

DatabaseConfig = DatabaseDebugConfig() if SettingsConfig.debug else DatabaseDeployConfig()

ServerConfig = ServerDebugConfig() if SettingsConfig.debug else None
