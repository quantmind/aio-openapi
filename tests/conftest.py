import asyncio
import os
import shutil
from unittest import mock

import pytest
from aiohttp.test_utils import TestClient
from aiohttp.web import Application
from sqlalchemy_utils import create_database, database_exists

from openapi.db.dbmodel import CrudDB
from openapi.testing import app_cli, with_test_db

from .example.db import DB
from .example.main import create_app


@pytest.fixture(scope="session")
def sync_url() -> str:
    return str(DB.sync_engine.url)


@pytest.fixture(autouse=True)
def clean_migrations():
    if os.path.isdir("migrations"):
        shutil.rmtree("migrations")


@pytest.fixture(autouse=True)
def sentry_mock(mocker):
    mm = mock.MagicMock()
    mocker.patch("sentry_sdk.init", mm)
    return mm


@pytest.fixture(scope="module", autouse=True)
def event_loop():
    """Return an instance of the event loop."""
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
def clear_db(sync_url) -> CrudDB:
    if not database_exists(sync_url):
        # drop_database(url)
        create_database(sync_url)
    else:
        DB.drop_all_schemas()
    return DB


@pytest.fixture
async def cli(clear_db: CrudDB) -> TestClient:
    app = create_app().web()
    with with_test_db(app["db"]):
        async with app_cli(app) as cli:
            yield cli


@pytest.fixture(scope="module")
async def cli2(clear_db: CrudDB) -> TestClient:
    app = create_app().web()
    with with_test_db(app["db"]):
        async with app_cli(app) as cli:
            yield cli


@pytest.fixture
def test_app(cli: TestClient) -> Application:
    return cli.app


@pytest.fixture
def db(test_app: Application) -> CrudDB:
    return test_app["db"]
