from datetime import datetime

from openapi.db import CrudDB
from openapi.utils import one_only


async def test_upsert(db: CrudDB) -> None:
    task = one_only(
        await db.db_upsert(db.tasks, dict(title="Example"), dict(severity=4))
    )
    assert task["id"]
    assert task["severity"] == 4
    assert task["done"] is None
    task2 = one_only(
        await db.db_upsert(db.tasks, dict(title="Example"), dict(done=datetime.now()))
    )
    task2["id"] == task["id"]
    assert task2["done"]


async def test_upsert_no_data(db: CrudDB) -> None:
    task = one_only(await db.db_upsert(db.tasks, dict(title="Example2")))
    assert task["id"]
    assert task["title"] == "Example2"
