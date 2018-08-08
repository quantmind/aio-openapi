import asyncio
import os
import shutil

import dotenv

import pytest

from aiohttp import test_utils

from sqlalchemy_utils import database_exists, drop_database, create_database

from openapi import db
from openapi.json import dumps
from openapi.rest import rest
from . import example


dotenv.load_dotenv()

DEFAULT_DB = 'postgres://postgres:postgres@localhost:5432/openapi'


def setup_app(app):
    db.setup_app(app)
    example.setup_app(app)


@pytest.fixture(scope='session', autouse=True)
def db_url():
    url = os.environ.get('DATASTORE') or DEFAULT_DB
    if database_exists(url):
        drop_database(url)
    create_database(url)
    return url


@pytest.fixture(autouse=True)
def test_app(db_url):
    os.environ['DATASTORE'] = db_url
    cli = rest(setup_app=setup_app)
    app = cli.web()
    app['db'].create_all()
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


@pytest.fixture
async def cli(loop, test_app):
    server = test_utils.TestServer(test_app, loop=loop)
    client = test_utils.TestClient(server, loop=loop, json_serialize=dumps)
    await client.start_server()
    yield client
    await client.close()


@pytest.fixture(autouse=True)
def clean_db(test_app):
    test_app['db'].drop_all()
