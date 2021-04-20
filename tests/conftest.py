import asyncio
import os
import shutil
from unittest import mock

import pytest
from aiohttp.test_utils import TestClient, TestServer
from aiohttp.web import Application
from sqlalchemy_utils import create_database, database_exists

from openapi.db.dbmodel import CrudDB
from openapi.json import dumps
from openapi.testing import with_test_db

from .example.db import DB
from .example.main import create_app


@pytest.fixture(scope="session")
def sync_url() -> str:
    url = str(DB)
    return url.replace("+asyncpg", "")


@pytest.fixture(autouse=True)
def clean_migrations():
    if os.path.isdir("migrations"):
        shutil.rmtree("migrations")


@pytest.fixture(autouse=True)
def sentry_mock(mocker):
    mm = mock.MagicMock()
    mocker.patch("sentry_sdk.init", mm)
    return mm


@pytest.fixture(scope="session", autouse=True)
def loop():
    """Return an instance of the event loop."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
async def clear_db(sync_url) -> CrudDB:
    if not database_exists(sync_url):
        # drop_database(url)
        create_database(sync_url)
    # await DB.drop_all_schemas()
    return DB


@pytest.fixture
async def cli(loop, clear_db: CrudDB) -> TestClient:
    app_cli = create_app()
    app = app_cli.web()
    client = TestClient(TestServer(app, loop=loop), loop=loop, json_serialize=dumps)
    try:
        async with with_test_db(app["db"]):
            await client.start_server()
            yield client
    finally:
        await client.close()


@pytest.fixture
async def test_app(cli: TestClient) -> Application:
    return cli.app


@pytest.fixture
async def db(test_app: Application) -> CrudDB:
    return test_app["db"]
