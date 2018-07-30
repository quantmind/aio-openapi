import asyncio
import os
import shutil

import pytest

from aiohttp import test_utils

from openapi import db
from openapi.db.utils import create_database, create_tables
from openapi.json import dumps
from openapi.rest import rest
from . import example


DEFAULT_DB = 'postgres://postgres:postgres@localhost:5432/postgres'


def setup_app(app):
    db.setup_app(app)
    example.setup_app(app)


@pytest.fixture(scope='session')
def test_app():
    if not os.environ.get('DATASTORE'):
        os.environ['DATASTORE'] = DEFAULT_DB
    cli = rest(setup_app=setup_app)
    cli.load_dotenv()
    app = cli.web()
    return app


@pytest.fixture(autouse=True)
def clean_migrations():
    """Return an instance of the event loop."""
    if os.path.isdir('migrations'):
        shutil.rmtree('migrations')


@pytest.fixture(autouse=True)
def loop():
    """Return an instance of the event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session', autouse=True)
def db_engine():
    cli = rest(setup_app=setup_app)
    cli.load_dotenv()
    if not os.environ.get('DATASTORE'):
        os.environ['DATASTORE'] = DEFAULT_DB
    app = cli.web()
    db_engine = create_database(app, 'openapi_unit_test')
    app['store'] = db_engine
    create_tables(app)
    return db_engine


@pytest.fixture
async def cli(loop, db_engine):
    app = rest(setup_app=setup_app).web()
    app['store'] = db_engine

    server = test_utils.TestServer(app, loop=loop)
    client = test_utils.TestClient(server, loop=loop, json_serialize=dumps)
    await client.start_server()
    yield client
    await client.close()


@pytest.fixture
def clean_db(db_engine):
    db_engine.execute('truncate table tasks')
