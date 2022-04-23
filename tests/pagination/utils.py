from collections import defaultdict

import async_timeout
import yarl
from factory import Factory, Faker, fuzzy
from yarl import URL

from openapi.testing import json_body

GROUPS = ("group1", "group2", "group3")


class SerieFactory(Factory):
    class Meta:
        model = dict

    value = Faker("pydecimal", positive=True, left_digits=6, right_digits=5)
    date = Faker("date_time_between", start_date="-2y")
    group = fuzzy.FuzzyChoice(GROUPS)


async def direction_asc(cli, series: list, path: str, limit: int = 15):
    response = await cli.get(path)
    data = await json_body(response)
    assert len(data) == 0
    all_groups = defaultdict(list)
    total = 0
    for group in GROUPS:
        values = all_groups[group]
        async for data in traverse_pagination(
            cli, path, dict(limit=limit, group=group)
        ):
            values.extend(data)
        total += len(values)
        for d1, d2 in zip(values[:-1], values[1:]):
            assert d1["date"] > d2["date"]

    assert total == len(series)
    return total


async def direction_desc(cli, series, path: str, limit: int = 10, **kwargs):
    all_groups = defaultdict(list)
    total = 0
    for group in GROUPS:
        values = all_groups[group]
        async for data in traverse_pagination(
            cli, path, dict(limit=limit, group=group, **kwargs)
        ):
            values.extend(data)
        total += len(values)
        for d1, d2 in zip(values[:-1], values[1:]):
            assert d1["date"] < d2["date"]

    assert total == len(series)
    return total


async def traverse_pagination(
    cli,
    path: str,
    params,
    *,
    timeout: float = 10000,
    test_prev: bool = True,
):
    url = yarl.URL("https://fake.com").with_path(path).with_query(params)
    async with async_timeout.timeout(timeout):
        batch = []
        while True:
            response = await cli.get(url.path_qs)
            data = await json_body(response)
            yield data
            next = response.links.get("next")
            if not next:
                break
            url: URL = next["url"]
            batch.append((data, url))
        if test_prev:
            prev = response.links.get("prev")
            while prev:
                url: URL = prev["url"]
                response = await cli.get(url.path_qs)
                data = await json_body(response)
                pdata, next_url = batch.pop()
                prev = response.links.get("prev")
                assert data == pdata
                assert next_url == response.links.get("next")["url"]
            assert batch == []
