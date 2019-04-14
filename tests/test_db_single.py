import pytest

from openapi.testing import SingleConnDatabase


@pytest.fixture
async def app(test_app):
    db = test_app["db"]
    test_app["db"] = SingleConnDatabase(db.dsn, db.metadata)
    yield test_app
    await test_app["db"].close()


async def test_connection(app):
    db = app["db"]
    conn1 = await db.get_connection()
    conn2 = await db.get_connection()
    assert conn1 == conn2


async def test_rollback(app):
    db = app["db"]
    async with db.rollback():
        rows = await db.db_insert(db.tasks, dict(title="testing rollback"))
        assert len(rows) == 1
        assert rows[0]["title"] == "testing rollback"
        id_ = rows[0]["id"]
        assert id_
        rows = await db.db_select(db.tasks, dict(id=id_))
        assert len(rows) == 1
    rows = await db.db_select(db.tasks, dict(id=id_))
    assert not rows
