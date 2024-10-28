"""This module initializes the database."""

import warnings

from sqlalchemy_utils import create_database, database_exists

from desdeo.api import db_models
from desdeo.api.config import ServerDebugConfig, SettingsConfig
from desdeo.api.db import Base, SessionLocal, engine
from desdeo.api.routers.user_authentication import get_password_hash
from desdeo.api.schema import UserPrivileges, UserRole

if __name__ == "__main__":
    if SettingsConfig.debug:
        # debug stuff

        print("Creating database tables.")
        if not database_exists(engine.url):
            create_database(engine.url)
        else:
            warnings.warn("Database already exists. Clearing it.", stacklevel=1)
            # Drop all tables
            Base.metadata.drop_all(bind=engine)
        print("Database tables created.")

        # Create the tables in the database.
        Base.metadata.create_all(bind=engine)

        # Create analyst test user
        db = SessionLocal()
        user_analyst = db_models.User(
            username=ServerDebugConfig.test_user_analyst_name,
            password_hash=get_password_hash(ServerDebugConfig.test_user_analyst_password),
            role=UserRole.ANALYST,
            privileges=[UserPrivileges.EDIT_USERS, UserPrivileges.CREATE_PROBLEMS],
            user_group="",
        )
        db.add(user_analyst)
        db.commit()
        db.refresh(user_analyst)

        # add first test DM user
        user_dm1 = db_models.User(
            username=ServerDebugConfig.test_user_dm1_name,
            password_hash=get_password_hash(ServerDebugConfig.test_user_dm1_password),
            role=UserRole.DM,
            privileges=[],
            user_group="",
        )
        db.add(user_dm1)
        db.commit()
        db.refresh(user_dm1)

        # add second test DM user
        user_dm2 = db_models.User(
            username=ServerDebugConfig.test_user_dm2_name,
            password_hash=get_password_hash(ServerDebugConfig.test_user_dm2_password),
            role=UserRole.DM,
            privileges=[],
            user_group="",
        )
        db.add(user_dm2)
        db.commit()
        db.refresh(user_dm2)

        db.close()

    else:
        # deployment stuff
        pass
