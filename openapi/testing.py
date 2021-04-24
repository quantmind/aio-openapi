"""Testing utilities
"""
import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from aiohttp.client import ClientResponse

from .db import CrudDB, Database
from .json import dumps, loads
from .types import Connection


async def json_body(response: ClientResponse, status: int = 200) -> Any:
    assert response.content_type == "application/json"
    data = await response.json(loads=loads)
    if response.status != status:  # pragma: no cover
        print(dumps({"status": response.status, "data": data}, indent=4))

    assert response.status == status
    return data


@contextmanager
def with_test_db(db: CrudDB) -> CrudDB:
    db.create_all()
    try:
        yield db
    finally:
        db.drop_all_schemas()


class SingleConnDatabase(CrudDB):
    """Useful for speedup testing"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lock = asyncio.Lock()
        self._connection = None

    @classmethod
    def from_db(cls, db: Database) -> "SingleConnDatabase":
        return cls(dsn=db.dsn, metadata=db.metadata)

    async def __aenter__(self) -> "SingleConnDatabase":
        self._connection = await self.engine.begin()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        transaction = self._connection.get_transaction()
        await transaction.rollback()
        self._connection = None

    @asynccontextmanager
    async def connection(self) -> Connection:
        async with self._lock:
            yield self._connection

    @asynccontextmanager
    async def transaction(self) -> Connection:
        async with self._lock:
            yield self._connection
