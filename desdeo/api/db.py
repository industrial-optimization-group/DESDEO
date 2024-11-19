"""Database configuration file for the API."""

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session

from desdeo.api.config import DatabaseDebugConfig, SettingsConfig

if SettingsConfig.debug:
    # debug and development stuff

    # SQLite setup
    # engine = create_engine(DatabaseDebugConfig.db_database, connect_args={"check_same_thread": False})
    engine = create_async_engine(DatabaseDebugConfig.db_database, connect_args={"check_same_thread": False})

else:
    # deployment stuff

    # Postgresql setup
    # check from config.toml
    # SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    pass


async def get_session():
    """Yield the current database session."""
    with Session(engine) as session:
        yield session
