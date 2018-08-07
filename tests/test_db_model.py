from openapi.db.dbmodel import DbModel


async def test_get_update(cli):
    tasks = DbModel(cli.app, 'tasks')
    assert tasks.db
    assert tasks.db_table.key == 'tasks'
