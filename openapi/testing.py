"""Testing utilities
"""
import asyncio
from typing import Any

from aiohttp.client import ClientResponse
from asyncpg import Connection
from asyncpg.transaction import Transaction

from .db.dbmodel import CrudDB
from .json import dumps, loads
from .utils import asynccontextmanager


async def json_body(response: ClientResponse, status: int = 200) -> Any:
    assert response.content_type == "application/json"
    data = await response.json(loads=loads)
    if response.status != status:  # pragma: no cover
        print(dumps({"status": response.status, "data": data}, indent=4))

    assert response.status == status
    return data


# backward compatibility
jsonBody = json_body


def equal_dict(d1, d2):
    """Check if two dictionaries are the same"""
    d1, d2 = map(dumps, (d1, d2))
    return d1 == d2


class SingleConnDatabase(CrudDB):
    """Useful for speedup testing
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._conn = None
        self._lock = asyncio.Lock()

    async def get_connection(self) -> Connection:
        if not self._conn:
            self._conn = await super().get_connection()
        return self._conn

    @asynccontextmanager
    async def connection(self) -> Connection:
        async with self._lock:
            conn = await self.get_connection()
            yield conn

    @asynccontextmanager
    async def rollback(self) -> Transaction:
        """Async context manager for rolling back a transaction.

        Very useful for speeding up tests
        """
        conn = await self.get_connection()
        transaction = conn.transaction()
        await transaction.start()
        yield transaction
        await transaction.rollback()

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                await self.release_connection(self._conn)
                self._conn = None
        await super().close()
