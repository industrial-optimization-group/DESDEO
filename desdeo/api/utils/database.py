"""Database utils for the API."""

from os import getenv
from typing import TypeVar, Dict

from sqlalchemy.engine import URL, Result
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, AsyncScalarResult
from sqlalchemy.future import select as sa_select
from sqlalchemy.orm import DeclarativeMeta, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import Executable
from sqlalchemy.sql.expression import exists as sa_exists, delete as sa_delete, Delete, update as sa_update, Update
from sqlalchemy.sql.functions import count
from sqlalchemy.sql.selectable import Select, Exists

from desdeo.api import DBConfig
from .logger import get_logger

T = TypeVar("T")

def select(entity) -> Select:
    """Shortcut for :meth:`sqlalchemy.future.select`

    Args:
        entity (sqlalchemy.sql.expression.FromClause): Entities / DB model to SELECT from.

    Returns:
        Select: A Select class object
    """
    return sa_select(entity)

def update(entity) -> Update:
    """Shortcut for :meth:`sqlalchemy.sql.expression.update`

    Args:
        entity (sqlalchemy.sql.expression.FromClause): Entities / DB model to SELECT from.

    Returns:
        Update: A Update class object
    """
    return sa_update(entity)

def filter_by(cls, *args, **kwargs) -> Select:
    """Shortcut for :meth:`sqlalchemy.future.Select.filter_by`

    Args:
        cls (sqlalchemy.sql.expression.FromClause): Entities / DB model to SELECT from.
        *args (tuple): Positional arguments.
        **kwargs (dict): Keyword arguments.

    Returns:
        Select: A Select class object with a WHERE clause
    """
    return select(cls, *args).filter_by(**kwargs)


def exists(*entities, **kwargs) -> Exists:
    """Shortcut for :meth:`sqlalchemy.sql.expression.exists`

    Args:
        *entities (tuple): Positional arguments.
        **kwargs (dict): Keyword arguments.

    Returns:
        Exists: A new Exists construct
    """
    return sa_exists(*entities, **kwargs)


def delete(table) -> Delete:
    """Shortcut for :meth:`sqlalchemy.sql.expression.delete`

    Args:
        table (sqlalchemy.sql.expression.FromClause): Entities / DB model.

    Returns:
        Delete: A Delete object
    """
    return sa_delete(table)


class DB:
    """An async SQLAlchemy ORM wrapper"""

    Base: DeclarativeMeta
    _engine: AsyncEngine
    _session: AsyncSession
    _Session: sessionmaker

    def __init__(self, driver: str, options: Dict = {"pool_size": 20, "max_overflow": 20}, **kwargs):
        """
        Args:
            driver (str): Drivername for db url.
            options (Dict, optional): Options for AsyncEngine instance.
            **kwargs (dict): Keyword arguments.
        """
        url: str = URL.create(drivername=driver, **kwargs)
        self._engine = create_async_engine(url, echo=True, pool_pre_ping=True, pool_recycle=300, **options)
        self.Base = declarative_base()
        self._Session = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)
        self._session: AsyncSession = self._Session()

    async def create_tables(self):
        """Creates all Model Tables"""
        async with self._engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.create_all)

    async def add(self, obj: T) -> T:
        """Adds an Row to the Database.

        Args:
            obj (T): Object to add.

        Returns:
            T: Added object.
        """
        self._session.add(obj)
        return obj

    async def delete(self, obj: T) -> T:
        """Deletes a Row from the Database

        Args:
            obj (T): Object to delete.

        Returns:
            T: Deleted object.
        """
        await self._session.delete(obj)
        return obj


    async def update(self, statement: Executable, *args, **kwargs) -> list[T] | None:
        """Executes a 'update' SQL Statement

        Args:
            statement (Executable): SQL statement.
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            list[T] | None: List of updated rows or None.
        """
        async with self._engine.begin() as conn:
            result = await conn.execute(statement, *args, **kwargs)
            return [x for x in result.fetchall()] if 'returning' in str(statement).lower() else None

    async def exec(self, statement: Executable, *args, **kwargs) -> Result:
        """Executes a SQL Statement

        Args:
            statement (Executable): SQL statement.
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            Result: A buffered Result object.
        """
        async with self._Session() as session:
            return await session.execute(statement, *args, **kwargs)

    async def all(self, statement: Executable, *args, **kwargs) -> list[T]:
        """Returns all matches for a Query

        Args:
            statement (Executable): SQL statement.
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            list[T]: List of rows.
        """
        return [x for x in (await self.exec(statement, *args, **kwargs)).scalars()]

    async def first(self, *args, **kwargs) -> dict | None:
        """Returns first match for a Query

        Args:
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            dict | None: First match for the Query, or None if there is no match.
        """
        return (await self.exec(*args, **kwargs)).scalar()

    async def exists(self, *args, **kwargs) -> bool:
        """Checks if there is a match for this Query

        Args:
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            bool: Whether there is a match for this Query
        """
        return await self.first(exists(*args, **kwargs).select())

    async def count(self, *args, **kwargs) -> int:
        """Counts matches for a Query

        Args:
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            int: Number of matches for a Query
        """
        return await self.first(select(count()).select_from(*args, **kwargs))

    async def commit(self):
        """Commits/Saves changes to Database"""
        await self._session.commit()


logger = get_logger(__name__)

DB_HOST = DBConfig.db_host
DB_PORT = DBConfig.db_port
DB_DATABASE = DBConfig.db_database
DB_USERNAME = DBConfig.db_username
DB_PASSWORD = DBConfig.db_password
DB_POOL_SIZE = DBConfig.db_pool_size
DB_MAX_OVERFLOW = DBConfig.db_max_overflow
DB_POOL = DBConfig.db_pool


class DatabaseDependency:
    db: DB
    database_url_options: Dict
    engine_options: Dict
    initialised: bool = False

    def __init__(self):
        self.database_url_options = {
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_DATABASE,
            "username": DB_USERNAME,
            "password": DB_PASSWORD,
        }
        self.database_url_options = dict([(k, v) for k, v in self.database_url_options.items() if v != ""])
        self.engine_options: Dict = {
            "pool_size": DB_POOL_SIZE,
            "max_overflow": DB_MAX_OVERFLOW,
            "poolclass": DB_POOL,
        }
        self.engine_options = dict([(k, int(v)) for k, v in self.engine_options.items() if v != ""])
        if self.engine_options["poolclass"] == 0:
            self.engine_options["poolclass"] = NullPool
        else:
            del self.engine_options["poolclass"]
        self.db = DB(
            getenv("DB_DRIVER", "postgresql+asyncpg"), options=self.engine_options, **self.database_url_options
        )
        logger.info("Connected to Database")

    async def init(self) -> None:
        if self.initialised:
            return
        # logger.info("Create Tables")
        self.initialised = True
        # await self.db.create_tables()

    async def __call__(self) -> DB:
        if not self.initialised:
            await self.init()
        return self.db


database_dependency: DatabaseDependency = DatabaseDependency()
Base: DeclarativeMeta = database_dependency.db.Base