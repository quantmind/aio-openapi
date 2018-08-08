import pytest


async def test_get_update(cli):
    tasks = cli.app['db'].model('tasks')
    assert tasks.db
    assert tasks.db_table.key == 'tasks'


async def test_get_attr(cli):
    db = cli.app['db']
    assert db.tasks is db.metadata.tables['tasks']
    with pytest.raises(AttributeError):
        db.fooooo
