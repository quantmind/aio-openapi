import os
from datetime import datetime

from click.testing import CliRunner

from openapi.testing import jsonBody


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


async def tests_get_list(cli):
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


async def tests_create(cli):
    response = await cli.post('/tasks', json=dict(title='test 1'))
    data = await jsonBody(response, 201)
    assert data['id'] == 1
    assert data['title'] == 'test 1'


async def tests_get_update(cli):
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


async def tests_delete_list(cli):
    response = await cli.delete('/tasks')
    assert response.status == 204
    await cli.post('/tasks', json=dict(title='bla'))
    await cli.post('/tasks', json=dict(title='foo'))
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


async def tests_create_list(cli):
    tasks = [dict(title='foo'), dict(title='bar')]
    response = await cli.post('/bulk/tasks', json=tasks)
    data = await jsonBody(response, status=201)
    titles = list(map(lambda t: t['title'], data))
    assert len(titles) == 2
    assert 'foo' in titles
    assert 'bar' in titles
