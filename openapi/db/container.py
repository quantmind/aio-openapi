import asyncpg

import sqlalchemy as sa

from ..utils import asynccontextmanager
from ..exc import ImproperlyConfigured


class Database:
    """A container for tables in a database
    """
    def __init__(self, dsn: str=None):
        self._dsn = dsn
        self._pool = None
        self._engine = None
        self._metadata = sa.MetaData()

    def __repr__(self):
        return self._dsn
    __str__ = __repr__

    @property
    def metadata(self):
        return self._metadata

    @property
    def pool(self):
        return self._pool

    @property
    def engine(self):
        if self._engine is None:
            if not self._dsn:
                raise ImproperlyConfigured('DSN not available')
            self._engine = sa.create_engine(self._dsn)
        return self._engine

    def __getattr__(self, name):
        if name in self._metadata.tables:
            return self._metadata.tables[name]
        return super().__getattribute__(name)

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn)

    @asynccontextmanager
    async def connection(self) -> asyncpg.Connection:
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> asyncpg.Connection:
        async with self.connection() as conn, conn.transaction():
            yield conn

    @asynccontextmanager
    async def ensure_connection(self, conn):
        if conn:
            yield conn
        else:
            async with self.connection() as conn:
                async with conn.transaction():
                    yield conn

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    # SQL Alchemy Sync Operations
    def create_all(self) -> None:
        self.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        self.engine.execute(f'truncate {", ".join(self.metadata.tables)}')
        try:
            self.engine.execute('drop table alembic_version')
        except Exception:  # noqa
            pass

    def drop_all_schemas(self) -> None:
        self.engine.execute("DROP SCHEMA IF EXISTS public CASCADE")
        self.engine.execute("CREATE SCHEMA IF NOT EXISTS public")
