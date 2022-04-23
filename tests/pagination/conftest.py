import pytest
from factory import Factory, Faker, fuzzy

from openapi.db.dbmodel import CrudDB

GROUPS = ("group1", "group2", "group3")


class SerieFactory(Factory):
    class Meta:
        model = dict

    value = Faker("pydecimal", positive=True, left_digits=6, right_digits=5)
    date = Faker("date_time_between", start_date="-2y")
    group = fuzzy.FuzzyChoice(GROUPS)


@pytest.fixture(scope="module")
async def series(cli2):
    db: CrudDB = cli2.app["db"]
    series = SerieFactory.create_batch(200)
    await db.db_insert(db.series, series)
    return series
