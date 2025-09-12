"""Database configuration file for the API."""

from sqlmodel import Session, create_engine

from desdeo.api.config import DatabaseDebugConfig, SettingsConfig
import os

"""
if SettingsConfig.debug:
    # debug and development stuff

    # SQLite setup
    engine = create_engine(DatabaseDebugConfig.db_database, connect_args={"check_same_thread": False})

else:
    # deployment stuff

    # Postgresql setup
    # check from config.toml
    # SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    pass
"""

if SettingsConfig.debug:
    # debug and development stuff

    # SQLite setup
    engine = create_engine(DatabaseDebugConfig.db_database, connect_args={"check_same_thread": False})

else:
    # For rahti purposes, read necessary fields from environment.
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


def get_session():
    """Yield the current database session."""
    with Session(engine) as session:
        yield session
