"""Database configuration file for the API."""
# The config should be in a separate file, but for simplicity, we will keep it here for now.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_USER = "user"
DB_PASSWORD = "password"  # NOQA: S105
DB_HOST = "postgresserver"
DB_NAME = "db"


SQLALCHEMY_DATABASE_URL = "postgresql://" + DB_USER + ":" + DB_PASSWORD + "@" + DB_HOST + "/" + DB_NAME

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
