from typing import Dict, NamedTuple

import async_timeout
import yarl
from aiohttp.web import Application
from yarl import URL

from openapi.testing import json_body


class FakeRequest(NamedTuple):
    app: Application
    headers: Dict
    url: yarl.URL

    @classmethod
    def from_app(cls, app: Application) -> "FakeRequest":
        return cls(app, {}, yarl.URL("https://fake.com"))


async def traverse_pagination(
    cli,
    path: str,
    params,
    *,
    timeout: float = 5,
    test_prev: bool = False,
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
            batch.append(data)
        if test_prev:
            prev = response.links.get("prev")
            while prev:
                url: URL = prev["url"]
                response = await cli.get(url.path_qs)
                data = await json_body(response)
                prev = response.links.get("prev")
                assert data == batch.pop()
            assert batch == []
