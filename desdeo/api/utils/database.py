"""Database utils for the API."""

from os import getenv
from typing import TypeVar

from sqlalchemy.engine import URL, Result
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncScalarResult,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.future import select as sa_select
from sqlalchemy.orm import DeclarativeMeta, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import Executable
from sqlalchemy.sql.expression import Delete
from sqlalchemy.sql.expression import delete as sa_delete
from sqlalchemy.sql.expression import exists as sa_exists
from sqlalchemy.sql.functions import count
from sqlalchemy.sql.selectable import Exists, Select

from desdeo.api.config import SettingsConfig

from .logger import get_logger

if SettingsConfig.debug:
    from desdeo.api.config import DatabaseDebugConfig

    DBConfig = DatabaseDebugConfig
else:
    # set development setting, e.g., DBConfig = DatabaseDeployConfig
    pass

T = TypeVar("T")


def select(entity) -> Select:
    """Shortcut for :meth:`sqlalchemy.future.select`.

    Args:
        entity (sqlalchemy.sql.expression.FromClause): Entities / DB model to SELECT from.

    Returns:
        Select: A Select class object
    """
    return sa_select(entity)


def filter_by(cls, *args, **kwargs) -> Select:
    """Shortcut for :meth:`sqlalchemy.future.Select.filter_by`.

    Args:
        cls (sqlalchemy.sql.expression.FromClause): Entities / DB model to SELECT from.
        *args (tuple): Positional arguments.
        **kwargs (dict): Keyword arguments.

    Returns:
        Select: A Select class object with a WHERE clause
    """
    return select(cls, *args).filter_by(**kwargs)


def exists(*entities, **kwargs) -> Exists:
    """Shortcut for :meth:`sqlalchemy.sql.expression.exists`.

    Args:
        *entities (tuple): Positional arguments.
        **kwargs (dict): Keyword arguments.

    Returns:
        Exists: A new Exists construct
    """
    return sa_exists(*entities, **kwargs)


def delete(table) -> Delete:
    """Shortcut for :meth:`sqlalchemy.sql.expression.delete`.

    Args:
        table (sqlalchemy.sql.expression.FromClause): Entities / DB model.

    Returns:
        Delete: A Delete object
    """
    return sa_delete(table)


class DB:
    """An async SQLAlchemy ORM wrapper."""

    Base: DeclarativeMeta
    _engine: AsyncEngine
    _session: AsyncSession

    def __init__(self, driver: str, options: dict | None = None, **kwargs):
        """Init the class.

        Args:
            driver (str): Drivername for db url.
            options (dict, optional): Options for AsyncEngine instance.
            **kwargs (dict): Keyword arguments.
        """
        if options is None:
            options = {"pool_size": 20, "max_overflow": 20}

        url: str = URL.create(drivername=driver, **kwargs)
        self._engine = create_async_engine(url, echo=True, pool_pre_ping=True, pool_recycle=300, **options)
        self.Base = declarative_base()
        self._session: AsyncSession = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)()

    async def create_tables(self):
        """Creates all Model Tables."""
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
        """Deletes a Row from the Database.

        Args:
            obj (T): Object to delete.

        Returns:
            T: Deleted object.
        """
        await self._session.delete(obj)
        return obj

    async def exec(self, statement: Executable, *args, **kwargs) -> Result:
        """Executes a SQL Statement.

        Args:
            statement (Executable): SQL statement.
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            Result: A buffered Result object.
        """
        return await self._session.execute(statement, *args, **kwargs)

    async def stream(self, statement: Executable, *args, **kwargs) -> AsyncScalarResult:
        """Returns an Stream of Query Results.

        Args:
            statement (Executable): SQL statement.
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            AsyncScalarResult: An AsyncScalarResult filtering object.
        """
        return (await self._session.stream(statement, *args, **kwargs)).scalars()

    async def all(self, statement: Executable, *args, **kwargs) -> list[T]:
        """Returns all matches for a Query.

        Args:
            statement (Executable): SQL statement.
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            list[T]: List of rows.
        """
        return [x async for x in await self.stream(statement, *args, **kwargs)]

    async def first(self, *args, **kwargs) -> dict | None:
        """Returns first match for a Query.

        Args:
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            dict | None: First match for the Query, or None if there is no match.
        """
        return (await self.exec(*args, **kwargs)).scalar()

    async def exists(self, *args, **kwargs) -> bool:
        """Checks if there is a match for this Query.

        Args:
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            bool: Whether there is a match for this Query
        """
        return await self.first(exists(*args, **kwargs).select())

    async def count(self, *args, **kwargs) -> int:
        """Counts matches for a Query.

        Args:
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        Returns:
            int: Number of matches for a Query
        """
        return await self.first(select(count()).select_from(*args, **kwargs))

    async def commit(self):
        """Commits/Saves changes to Database."""
        await self._session.commit()


logger = get_logger(__name__)


class DatabaseDependency:
    """A class to represent a database dependency."""

    db: DB
    database_url_options: dict
    engine_options: dict
    initialized: bool = False

    def __init__(self):
        """Initialize the class."""
        self.database_url_options = {
            "host": DBConfig.db_host,
            "port": DBConfig.db_port,
            "database": DBConfig.db_database,
            "username": DBConfig.db_username,
            "password": DBConfig.db_password,
        }
        self.database_url_options = {k: v for k, v in self.database_url_options.items() if v != ""}
        self.engine_options: dict = {
            # "pool_size": DB_POOL_SIZE, ## not used by sqlite
            # "max_overflow": DB_MAX_OVERFLOW, ## not used by sqlite
            "poolclass": DBConfig.db_pool,
        }
        self.engine_options = {k: int(v) for k, v in self.engine_options.items() if v != ""}
        if self.engine_options["poolclass"] == 0:
            self.engine_options["poolclass"] = NullPool
        else:
            del self.engine_options["poolclass"]
        self.db = DB(
            getenv("DB_DRIVER", "postgresql+asyncpg"), options=self.engine_options, **self.database_url_options
        )
        logger.info("Connected to Database")

    async def init(self) -> None:
        """Set whether the dependency is initialized or not."""
        if self.initialized:
            return

        # logger.info("Create Tables")
        self.initialized = True
        # await self.db.create_tables()

    async def __call__(self) -> DB:
        """Define __call__."""
        if not self.initialized:
            await self.init()
        return self.db


database_dependency: DatabaseDependency = DatabaseDependency()
Base: DeclarativeMeta = database_dependency.db.Base
