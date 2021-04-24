import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from openapi.types import Connection
from openapi.utils import str2bool

from ..exc import ImproperlyConfigured

DBPOOL_MAX_SIZE = int(os.environ.get("DBPOOL_MAX_SIZE") or "10")
DBPOOL_MAX_OVERFLOW = int(os.environ.get("DBPOOL_MAX_OVERFLOW") or "10")
DBECHO = str2bool(os.environ.get("DBECHO") or "no")


class Database:
    """A container for tables in a database and a manager of asynchronous
    connections to a postgresql database

    :param dsn: Data source name used for database connections
    :param metadata: :class:`sqlalchemy.schema.MetaData` containing tables
    """

    def __init__(self, dsn: str = "", metadata: sa.MetaData = None) -> None:
        self._dsn = dsn
        self._metadata = metadata or sa.MetaData()
        self._engine = None

    def __repr__(self) -> str:
        return self._dsn

    __str__ = __repr__

    @property
    def dsn(self) -> str:
        """Data source name used for database connections"""
        return self._dsn

    @property
    def metadata(self) -> sa.MetaData:
        """The :class:`sqlalchemy.schema.MetaData` containing tables"""
        return self._metadata

    @property
    def engine(self) -> AsyncEngine:
        """The :class:`sqlalchemy.ext.asyncio.AsyncEngine` creating connection
        and transactions"""
        if self._engine is None:
            if not self._dsn:
                raise ImproperlyConfigured("DSN not available")
            self._engine = create_async_engine(
                self._dsn,
                echo=DBECHO,
                pool_size=DBPOOL_MAX_SIZE,
                max_overflow=DBPOOL_MAX_OVERFLOW,
            )
        return self._engine

    @property
    def sync_engine(self) -> Engine:
        """The :class:`sqlalchemy.engine.Engine` for synchrouns operations"""
        return create_engine(self._dsn.replace("+asyncpg", ""))

    def __getattr__(self, name: str) -> Any:
        """Retrive a :class:`sqlalchemy.schema.Table` from metadata tables

        :param name: if this is a valid table name in the tables of :attr:`.metadata`
            it returns the table, otherwise it defaults to superclass method
        """
        if name in self._metadata.tables:
            return self._metadata.tables[name]
        return super().__getattribute__(name)

    @asynccontextmanager
    async def connection(self) -> Connection:
        """Context manager for obtaining an asynchronous connection"""
        async with self.engine.connect() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> Connection:
        """Context manager for initializing an asynchronous database transaction"""
        async with self.engine.begin() as conn:
            yield conn

    @asynccontextmanager
    async def ensure_connection(self, conn: Optional[Connection] = None) -> Connection:
        """Context manager for ensuring we a connection has initialized
        a database transaction"""
        if conn:
            if not conn.in_transaction():
                async with conn.begin():
                    yield conn
            else:
                yield conn
        else:
            async with self.transaction() as conn:
                yield conn

    async def close(self) -> None:
        """Close the asynchronous db engine if opened"""
        if self._engine:
            engine, self._engine = self._engine, None
            await engine.dispose()

    # SQL Alchemy Sync Operations
    def create_all(self) -> None:
        """Create all tables defined in :attr:`metadata`"""
        self.metadata.create_all(self.sync_engine)

    def drop_all(self) -> None:
        """Drop all tables from :attr:`metadata` in database"""
        with self.sync_engine.begin() as conn:
            conn.execute(sa.text(f'truncate {", ".join(self.metadata.tables)}'))
            try:
                conn.execute(sa.text("drop table alembic_version"))
            except Exception:  # noqa
                pass

    def drop_all_schemas(self) -> None:
        """Drop all schema in database"""
        with self.sync_engine.begin() as conn:
            conn.execute(sa.text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(sa.text("CREATE SCHEMA IF NOT EXISTS public"))
