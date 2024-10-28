"""Database configuration file for the API."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from desdeo.api.config import DatabaseDebugConfig, SettingsConfig

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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """Get a database session as a dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
