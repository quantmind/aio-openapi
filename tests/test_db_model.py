

async def test_get_update(cli):
    tasks = cli.app['db'].model('tasks')
    assert tasks.db
    assert tasks.db_table.key == 'tasks'
