import asyncio
import os
import shutil

import pytest
from aiohttp import test_utils
from asynctest import CoroutineMock
from sqlalchemy_utils import create_database, database_exists, drop_database

from openapi.json import dumps

from .example.main import create_app

DEFAULT_DB = "postgresql://postgres:postgres@localhost:5432/openapi"


@pytest.fixture(autouse=True)
def clean_migrations():
    if os.path.isdir("migrations"):
        shutil.rmtree("migrations")


@pytest.fixture(autouse=True)
def sentry_mock(mocker):
    mock = CoroutineMock()
    mocker.patch("raven_aiohttp.AioHttpTransport._do_send", mock)
    return mock


@pytest.fixture(scope="session", autouse=True)
def loop():
    """Return an instance of the event loop."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def db_url():
    url = os.environ.get("DATASTORE") or DEFAULT_DB
    if database_exists(url):
        drop_database(url)
    create_database(url)
    return url


@pytest.fixture()
async def test_app(db_url):
    os.environ["DATASTORE"] = db_url
    cli = create_app()
    app = cli.web()
    app["db"].create_all()
    try:
        yield app
    finally:
        app["db"].drop_all_schemas()


@pytest.fixture
async def db(test_app):
    return test_app["db"]


@pytest.fixture
async def cli(loop, test_app):
    server = test_utils.TestServer(test_app, loop=loop)
    client = test_utils.TestClient(server, loop=loop, json_serialize=dumps)
    await client.start_server()
    try:
        yield client
    finally:
        await client.close()
