"""Tests for db utils."""
from desdeo.api.db_models import User as UserModel
from desdeo.api.utils.database import (
    database_dependency,
    select,
    filter_by,
    exists,
    delete,
    DB
)
from sqlalchemy.sql.expression import exists as sa_exists, delete as sa_delete
from sqlalchemy.future import select as sa_select
from fastapi import Depends
import pytest
from typing import Annotated
from sqlalchemy.dialects import postgresql
from desdeo.api.db_models import User as UserModel
from desdeo.api import db_models
from desdeo.api.schema import UserRole
from desdeo.api.routers.UserAuth import get_password_hash
from os import getenv


'''@pytest_asyncio.fixture(scope='session', autouse=True)
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()'''

pytestmark = pytest.mark.asyncio(scope='session')

async def test_select():
    """Test select()."""

    model = UserModel

    result = select(model)
    result2 = sa_select(model)

    assert result.compare(result2)

async def test_filter_by():
    """Test filter_by()."""

    model = UserModel

    filters = {
        "id": 1,
    }

    result = filter_by(model, **filters)
    result2 = select(model).filter_by(**filters)

    assert result.compare(result2)

async def test_exists():
    """Test exists()."""

    model = UserModel

    filters = {
        "id": 1,
    }
    query = filter_by(model, **filters)

    result = exists(query)
    result2 = sa_exists(query)

    assert result.compare(result2)

async def test_delete():
    """Test delete()."""

    model = UserModel

    result = delete(model)
    result2 = sa_delete(model)

    assert result.compare(result2)

async def test_add_row():
    """Test db's add()."""

    row = db_models.User(
      username="dummy",
      password_hash=get_password_hash("test"),
      role=UserRole.GUEST,
      privilages=[],
      user_group="",
    )

    db: DB = DB(getenv("DB_DRIVER", "postgresql+asyncpg"), {})
    #db = await database_dependency()

    await db.add(row)

    '''Do not commit for testing purpose'''
    # await db.commit()

async def test_db_count():
    """Test db's count() and all()."""

    db: DB = await database_dependency()

    user_count: int = await db.count(select(UserModel).subquery())
    users: List[Dict] = await db.all(select(UserModel))

    assert len(users) == user_count

async def test_db_exists():
    """Test db's exists() and first()."""

    db: DB = await database_dependency()

    exists = await db.exists(select(UserModel).filter_by(id=1))
    user: UserModel = await db.first(select(UserModel).filter_by(id=1))

    assert exists
    assert user.id == 1

async def test_delete_row():
    """Test db's delete()."""

    db: DB = await database_dependency()
    query = select(UserModel).filter_by(id=1)
    if not await db.exists(query):
        raise Exception("User doesn't exists")
    await db.delete(await db.first(query))

    '''Do not commit for testing purpose'''
    # await db.commit()