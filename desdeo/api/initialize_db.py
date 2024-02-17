"""This module initializes the database."""
import warnings

from sqlalchemy_utils import create_database, database_exists, drop_database

from desdeo.api import models
from desdeo.api.db import SessionLocal, engine
from desdeo.api.routers.UserAuth import UserPrivileges, UserRole, get_password_hash

TEST_USER = "test"
TEST_PASSWORD = "test"  # NOQA: S105 # TODO: Remove this line and create a proper user creation system.

# The following line creates the database and tables. This is not ideal, but it is simple for now.
# It recreates the tables every time the server starts. Any data saved in the database will be lost.
# TODO: Remove this line and create a proper database migration system.
print("Creating database tables.")
if not database_exists(engine.url):
    create_database(engine.url)
else:
    warnings.warn("Database already exists. Dropping and recreating it.", stacklevel=1)
    drop_database(engine.url)
    create_database(engine.url)
print("Database tables created.")

# Create the tables in the database.
models.Base.metadata.create_all(bind=engine)

# Create test users
db = SessionLocal()
db.add(
    models.User(
        username="test",
        password_hash=get_password_hash("test"),
        role=UserRole.ANALYST,
        privilages=[UserPrivileges.EDIT_USERS, UserPrivileges.CREATE_PROBLEMS],
        user_group="",
    )
)
db.commit()
db.close()
