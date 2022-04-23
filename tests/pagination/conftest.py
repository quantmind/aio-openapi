import pytest

from openapi.db.dbmodel import CrudDB

from .utils import SerieFactory


@pytest.fixture(scope="module")
async def series(cli2):
    db: CrudDB = cli2.app["db"]
    series = SerieFactory.create_batch(200)
    await db.db_insert(db.series, series)
    return series
