from openapi.testing import CrudDB, SingleConnDatabase


async def __test_rollback(db: CrudDB):
    async with SingleConnDatabase.from_db(db) as sdb:
        rows = await sdb.db_insert(sdb.tasks, dict(title="testing rollback"))
        assert rows.rowcount == 1
        row = rows.first()
        assert row["title"] == "testing rollback"
        id_ = row["id"]
        assert id_
        rows = await sdb.db_select(sdb.tasks, dict(id=id_))
        assert rows.rowcount == 1
    rows = await sdb.db_select(sdb.tasks, dict(id=id_))
    assert rows.rowcount == 0
