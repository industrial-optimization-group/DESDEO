"""Database configuration file for the API."""
# The config should be in a separate file, but for simplicity, we will keep it here for now.

import warnings
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_utils import create_database, database_exists, drop_database

from desdeo.api.config import DBConfig

# TODO: Extract this to a config file.
DB_USER = DBConfig.db_username
DB_PASSWORD = DBConfig.db_password
DB_HOST = DBConfig.db_host
DB_PORT = DBConfig.db_port
DB_NAME = DBConfig.db_database


SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get a database session as a dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
