"""Database configuration file for the API."""

from sqlalchemy import event
from sqlmodel import Session, create_engine

from desdeo.api.config import DatabaseConfig, SettingsConfig

if SettingsConfig.debug:
    # debug and development stuff

    # SQLite setup
    engine = create_engine(DatabaseConfig.db_database, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    DB_USER = DatabaseConfig.db_username
    DB_PASSWORD = DatabaseConfig.db_password
    DB_HOST = DatabaseConfig.db_host
    DB_PORT = DatabaseConfig.db_port
    DB_NAME = DatabaseConfig.db_database

    # Now the use of postgres is hardcoded for deployment, which may be fine
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


def get_session():
    """Yield the current database session."""
    with Session(engine) as session:
        yield session
