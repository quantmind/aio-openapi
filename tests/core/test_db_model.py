import pytest


async def test_get_attr(cli):
    db = cli.app["db"]
    assert db.tasks is db.metadata.tables["tasks"]
    with pytest.raises(AttributeError) as ex_info:
        db.fooooo
    assert "fooooo" in str(ex_info.value)


async def test_db_count(cli):
    db = cli.app["db"]
    n = await db.db_count(db.tasks, {})
    assert n == 0
    await db.db_insert(db.tasks, dict(title="testing rollback"))
    n = await db.db_count(db.tasks, {})
    assert n == 1
