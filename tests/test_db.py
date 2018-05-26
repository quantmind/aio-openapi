import os
import asyncio
from datetime import datetime

import pytest

from click.testing import CliRunner

from aiohttp import test_utils

from openapi.rest import rest
from openapi.json import dumps
from openapi.db.utils import create_database, create_tables
from openapi import db
from openapi.testing import jsonBody

from . import example


DEFAULT_DB = 'postgres://postgres:postgres@localhost:5432/postgres'


def setup_app(app):
    db.setup_app(app)
    example.setup_app(app)


@pytest.fixture(scope='session')
def loop():
    """Return an instance of the event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session')
def test_app():
    if not os.environ.get('DATASTORE'):
        os.environ['DATASTORE'] = DEFAULT_DB
    cli = rest(setup_app=setup_app)
    cli.load_dotenv()
    app = cli.web()
    engine = app.get('store')
    if engine:
        app['store'] = create_database(app, 'openapi_unit_test')
        create_tables(app)
    return app


@pytest.fixture(scope='session')
async def cli(loop, test_app):
    server = test_utils.TestServer(test_app, loop=loop)
    client = test_utils.TestClient(server, loop=loop, json_serialize=dumps)
    await client.start_server()
    yield client
    await client.close()


def test_db(cli):
    runner = CliRunner()
    result = runner.invoke(cli.app['cli'], ['db', '--help'])
    assert result.exit_code == 0
    assert result.output.startswith('Usage: root db [OPTIONS]')


async def tests_get_list(cli):
    response = await cli.get('/tasks')
    data = await jsonBody(response)
    assert len(data) == 0


async def test_get_404(cli):
    response = await cli.get('/tasks/101')
    await jsonBody(response, 404)
    response = await cli.patch('/tasks/101', json=dict(title='ciao'))
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
