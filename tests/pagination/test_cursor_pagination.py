from collections import defaultdict

import pytest
from factory import Factory, Faker, fuzzy

from openapi.db.dbmodel import CrudDB
from openapi.testing import json_body
from tests.utils import traverse_pagination

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


async def test_pagination_next_link(cli2, series):
    response = await cli2.get("/series")
    data = await json_body(response)
    assert len(data) == 0
    all_groups = defaultdict(list)
    total = 0
    for group in GROUPS:
        values = all_groups[group]
        async for data in traverse_pagination(
            cli2, "/series", dict(limit=10, group=group)
        ):
            values.extend(data)
        total += len(values)
        for d1, d2 in zip(values[:-1], values[1:]):
            assert d1["date"] > d2["date"]

    assert total == len(series)


async def test_order_by(cli2, series):
    all_groups = defaultdict(list)
    total = 0
    for group in GROUPS:
        values = all_groups[group]
        async for data in traverse_pagination(
            cli2, "/series", dict(limit=10, group=group, order_by="date")
        ):
            values.extend(data)
        total += len(values)
        for d1, d2 in zip(values[:-1], values[1:]):
            assert d1["date"] < d2["date"]

    assert total == len(series)
