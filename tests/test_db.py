import os
from datetime import datetime

from click.testing import CliRunner

from openapi.testing import jsonBody, equal_dict
from openapi.utils import error_dict


def test_db(cli):
    runner = CliRunner()
    result = runner.invoke(cli.app['cli'], ['db', '--help'])
    assert result.exit_code == 0
    assert result.output.startswith('Usage: root db [OPTIONS]')


def test_createdb(cli):
    runner = CliRunner()
    result = runner.invoke(cli.app['cli'], ['db', 'create', 'testing-aio-db'])
    assert result.exit_code == 0
    result = runner.invoke(
        cli.app['cli'], ['db', 'create', 'testing-aio-db', '--force'])
    assert result.exit_code == 0


async def test_migration_init(cli):
    runner = CliRunner()
    result = runner.invoke(cli.app['cli'], ['db', 'init'])
    assert result.exit_code == 0
    assert os.path.isdir('migrations')


def test_migrate(cli):
    runner = CliRunner()
    runner.invoke(cli.app['cli'], ['db', 'init'])
    result = runner.invoke(cli.app['cli'], ['db', 'migrate', '-m', 'test'])
    assert result.exit_code == 0


async def test_get_list(cli):
    response = await cli.get('/tasks')
    data = await jsonBody(response)
    assert len(data) == 0


async def test_get_404(cli):
    response = await cli.get('/tasks/101')
    await jsonBody(response, 404)
    response = await cli.get('/tasks/bla')
    await jsonBody(response, 404)
    response = await cli.patch('/tasks/101', json=dict(title='ciao'))
    await jsonBody(response, 404)
    response = await cli.patch('/tasks/bla', json=dict(title='ciao'))
    await jsonBody(response, 404)


async def test_400(cli):
    response = await cli.patch('/tasks/101')
    await jsonBody(response, 400)


async def test_create(cli):
    response = await cli.post('/tasks', json=dict(title='test 1', type='todo'))
    data = await jsonBody(response, 201)
    assert data['id'] == 1
    assert data['title'] == 'test 1'
    assert data['type'] == 'todo'


async def test_create_422(cli):
    response = await cli.post('/tasks', json=dict(severity=4))
    data = await jsonBody(response, 422)
    assert len(data['errors']) == 1
    errors = error_dict(data['errors'])
    assert errors['title'] == 'required'


async def test_get_update(cli):
    response = await cli.post('/tasks', json=dict(title='test 2'))
    data = await jsonBody(response, 201)
    assert data['id'] == 2
    assert data['title'] == 'test 2'
    #
    # now get it
    response = await cli.get('/tasks/2')
    await jsonBody(response, 200)
    #
    # now update
    response = await cli.patch(
        '/tasks/2', json=dict(done=datetime.now().isoformat())
    )
    data = await jsonBody(response, 200)
    assert data['id'] == 2
    #
    # now delete it
    response = await cli.delete('/tasks/2')
    assert response.status == 204
    response = await cli.get('/tasks/2')
    await jsonBody(response, 404)


async def test_delete_list(cli):
    response = await cli.delete('/tasks')
    assert response.status == 204
    response = await cli.post('/tasks', json=dict(title='bla'))
    d1 = await jsonBody(response, 201)
    response = await cli.post('/tasks', json=dict(title='foo'))
    d2 = await jsonBody(response, 201)
    assert not equal_dict(d1, d2)
    response = await cli.get('/tasks')
    data = await jsonBody(response)
    assert len(data) == 2
    response = await cli.patch(
        f'/tasks/{data[0]["id"]}', json=dict(done=datetime.now().isoformat())
    )
    response = await cli.get('/tasks', params={'done': 'true'})
    data = await jsonBody(response)
    assert len(data) == 1
    assert data[0]['done']
    response = await cli.delete('/tasks', params={'done': 'true'})
    assert response.status == 204
    response = await cli.get('/tasks')
    data = await jsonBody(response)
    assert len(data) == 1
    assert 'done' not in data[0]


async def test_create_list(cli):
    tasks = [dict(title='foo'), dict(title='bar')]
    response = await cli.post('/bulk/tasks', json=tasks)
    data = await jsonBody(response, status=201)
    titles = list(map(lambda t: t['title'], data))
    assert len(titles) == 2
    assert 'foo' in titles
    assert 'bar' in titles


async def test_spec_root(cli):
    response = await cli.get('/spec')
    spec = await jsonBody(response)
    assert 'paths' in spec
    assert 'tags' in spec
    assert len(spec['tags']) == 2
    assert spec['tags'][1]['name'] == 'task'
    assert spec['tags'][1]['description'] == 'simple description'


async def test_transaction_create(cli):
    response = await cli.post('/transaction/tasks', json=dict(title='tran'))
    data = await jsonBody(response, status=201)
    assert data['title'] == 'tran'


async def test_transaction_create_error(cli):
    response_tasks_before = await cli.get('/transaction/tasks')
    tasks_before = await jsonBody(response_tasks_before)
    response = await cli.post(
        '/transaction/tasks', json=dict(title='tran', should_raise=True)
    )
    await jsonBody(response, status=500)
    response_tasks_after = await cli.get('/transaction/tasks')
    tasks_after = await jsonBody(response_tasks_after)
    assert len(tasks_before) == len(tasks_after)


async def test_transaction_update(cli):
    response = await cli.post('/tasks', json=dict(title='tran'))
    task = await jsonBody(response, status=201)
    response = await cli.patch(
        f'/transaction/tasks/{task["id"]}', json=dict(title='newtask')
    )
    data = await jsonBody(response)
    assert data['title'] == 'newtask'


async def test_transaction_update_error(cli):
    response = await cli.post('/tasks', json=dict(title='tran'))
    task = await jsonBody(response, status=201)
    response = await cli.patch(
        f'/transaction/tasks/{task["id"]}',
        json=dict(title='newtask', should_raise=True)
    )
    await jsonBody(response, status=500)
    response = await cli.get(f'/transaction/tasks/{task["id"]}')
    data = await jsonBody(response)
    assert data['title'] == 'tran'


async def test_transaction_delete(cli):
    response = await cli.post('/tasks', json=dict(title='tran'))
    task = await jsonBody(response, status=201)
    response = await cli.delete(f'/transaction/tasks/{task["id"]}', json={})
    await jsonBody(response, status=204)
    response = await cli.get(f'/transaction/tasks/{task["id"]}')
    await jsonBody(response, status=404)


async def test_transaction_delete_error(cli):
    response = await cli.post('/tasks', json=dict(title='tran'))
    task = await jsonBody(response, status=201)
    response = await cli.delete(
        f'/transaction/tasks/{task["id"]}', json=dict(should_raise=True)
    )
    await jsonBody(response, status=500)
    response = await cli.get(f'/tasks/{task["id"]}')
    await jsonBody(response, 200)


async def test_transaction_get_list(cli):
    await cli.post('/tasks', json=dict(title='tran'))
    await cli.post('/tasks', json=dict(title='tran'))
    await cli.post('/tasks', json=dict(title='tran'))
    response = await cli.get('/transaction/tasks')
    await jsonBody(response)


async def test_transaction_create_list(cli):
    tasks = [dict(title='foo'), dict(title='bar')]
    response = await cli.post('/transaction/bulk/tasks', json=tasks)
    data = await jsonBody(response, status=201)
    titles = list(map(lambda t: t['title'], data))
    assert len(titles) == 2
    assert 'foo' in titles
    assert 'bar' in titles


async def test_transaction_delete_list(cli):
    response = await cli.delete('/transaction/bulk/tasks')
    assert response.status == 204
    tasks = [dict(title='bulk_created') for i in range(5)]
    response = await cli.post('/transaction/bulk/tasks', json=tasks)
    data = await jsonBody(response, 201)
    assert len(data) == 5

    response = await cli.delete(
        '/transaction/bulk/tasks', json=dict(title='bulk_created')
    )
    assert response.status == 204

    response = await cli.get(
        '/transaction/tasks', params={'title': 'bulk_created'}
    )
    data = await jsonBody(response)

    assert len(data) == 0
