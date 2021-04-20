import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from openapi.utils import str2bool

from ..exc import ImproperlyConfigured

DBPOOL_MIN_SIZE = int(os.environ.get("DBPOOL_MIN_SIZE") or "10")
DBPOOL_MAX_SIZE = int(os.environ.get("DBPOOL_MAX_SIZE") or "10")
DBECHO = str2bool(os.environ.get("DBECHO") or "no")


class Database:
    """A container for tables in a database and manager of asynchronous
    connections to a psotgresql database

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
        """The :class:`sqlalchemy.engine.Engine`"""
        if self._engine is None:
            if not self._dsn:
                raise ImproperlyConfigured("DSN not available")
            self._engine = create_async_engine(self._dsn, echo=DBECHO)
        return self._engine

    def __getattr__(self, name: str) -> Any:
        """Retrive a :class:`sqlalchemy.schema.Table` from metadata tables

        :param name: if this is a valid table name in the tables of :attr:`.metadata`
            it returns the table, otherwise it defaults to superclass method
        """
        if name in self._metadata.tables:
            return self._metadata.tables[name]
        return super().__getattribute__(name)

    @asynccontextmanager
    async def connection(self) -> AsyncConnection:
        async with self.engine.connect() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncConnection:
        async with self.engine.begin() as conn:
            yield conn

    @asynccontextmanager
    async def ensure_connection(
        self, conn: Optional[AsyncConnection] = None
    ) -> AsyncConnection:
        if conn:
            if not conn.in_transaction():
                with conn.begin():
                    yield conn
            else:
                yield conn
        else:
            async with self.engine.begin() as conn:
                yield conn

    async def close(self) -> None:
        """Close the connection :attr:`pool` if available"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None

    # SQL Alchemy Sync Operations
    async def create_all(self) -> None:
        """Create all tables defined in :attr:`metadata`"""
        async with self.transaction() as conn:
            await conn.run_sync(self.metadata.create_all)

    async def drop_all(self) -> None:
        """Drop all tables from :attr:`metadata` in database"""
        async with self.transaction() as conn:
            await conn.execute(sa.text(f'truncate {", ".join(self.metadata.tables)}'))
            try:
                await conn.execute(sa.text("drop table alembic_version"))
            except Exception:  # noqa
                pass

    async def drop_all_schemas(self) -> None:
        """Drop all schema in database"""
        async with self.engine.begin() as conn:
            await conn.execute(sa.text("DROP SCHEMA IF EXISTS public CASCADE"))
            await conn.execute(sa.text("CREATE SCHEMA IF NOT EXISTS public"))
