from collections import defaultdict

from openapi.testing import json_body
from tests.utils import traverse_pagination

from .conftest import GROUPS


async def test_direction_asc(cli2, series):
    response = await cli2.get("/series")
    data = await json_body(response)
    assert len(data) == 0
    all_groups = defaultdict(list)
    total = 0
    for group in GROUPS:
        values = all_groups[group]
        async for data in traverse_pagination(
            cli2, "/series", dict(limit=15, group=group)
        ):
            values.extend(data)
        total += len(values)
        for d1, d2 in zip(values[:-1], values[1:]):
            assert d1["date"] > d2["date"]

    assert total == len(series)


async def test_direction_desc(cli2, series):
    all_groups = defaultdict(list)
    total = 0
    for group in GROUPS:
        values = all_groups[group]
        async for data in traverse_pagination(
            cli2, "/series", dict(limit=10, group=group, direction="desc")
        ):
            values.extend(data)
        total += len(values)
        for d1, d2 in zip(values[:-1], values[1:]):
            assert d1["date"] < d2["date"]

    assert total == len(series)
