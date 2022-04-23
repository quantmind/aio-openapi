from typing import Dict

from yarl import URL

from openapi.pagination import offsetPagination
from openapi.testing import json_body

from .utils import direction_asc, direction_desc

OffsetPagination = offsetPagination("id")


def pag_links(total: int, limit: int, offset: int) -> Dict[str, URL]:
    return OffsetPagination(limit=limit, offset=offset).links(
        URL("http://test.com/path?a=2&b=3"), [], total
    )


def test_last_link():
    #
    links = pag_links(0, 25, 0)
    assert links == {}
    #
    links = pag_links(120, 25, 0)
    assert len(links) == 2
    assert links["next"]
    assert links["last"]
    assert links["next"].query["offset"] == "25"
    assert links["next"].query["limit"] == "25"
    assert links["last"].query["offset"] == "100"
    assert links["last"].query["limit"] == "25"
    #
    links = pag_links(120, 25, 75)
    assert len(links) == 4
    assert links["first"].query["offset"] == "0"
    assert links["prev"].query["offset"] == "50"
    assert links["last"].query["offset"] == "100"
    #
    links = pag_links(120, 25, 50)
    assert len(links) == 4
    assert links["first"].query["offset"] == "0"
    assert links["prev"].query["offset"] == "25"
    assert links["next"].query["offset"] == "75"
    assert links["last"].query["offset"] == "100"


async def test_pagination_next_link(cli):
    response = await cli.post("/tasks", json=dict(title="bla"))
    await json_body(response, 201)
    response = await cli.post("/tasks", json=dict(title="foo"))
    await json_body(response, 201)
    response = await cli.get("/tasks")
    data = await json_body(response)
    assert "Link" not in response.headers
    assert len(data) == 2


async def test_pagination_first_link(cli):
    response = await cli.post("/tasks", json=dict(title="bla"))
    await json_body(response, 201)
    response = await cli.post("/tasks", json=dict(title="foo"))
    await json_body(response, 201)
    response = await cli.get("/tasks", params={"limit": 10, "offset": 20})
    url = response.url
    data = await json_body(response)
    link = response.headers["Link"]
    assert link == (
        f'<{url.parent}{url.path}?limit=10&offset=0>; rel="first", '
        f'<{url.parent}{url.path}?limit=10&offset=10>; rel="prev"'
    )
    assert "Link" in response.headers
    assert len(data) == 0


async def test_invalid_limit_offset(cli):
    response = await cli.get("/tasks", params={"limit": "wtf"})
    await json_body(response, 422)
    response = await cli.get("/tasks", params={"limit": 0})
    await json_body(response, 422)
    response = await cli.get("/tasks", params={"offset": "wtf"})
    await json_body(response, 422)
    response = await cli.get("/tasks", params={"offset": -10})
    await json_body(response, 422)


async def test_pagination_with_forwarded_host(cli):
    response = await cli.post("/tasks", json=dict(title="bla"))
    await json_body(response, 201)
    response = await cli.post("/tasks", json=dict(title="foo"))
    await json_body(response, 201)
    response = await cli.get(
        "/tasks",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "whenbeer.pub",
            "X-Forwarded-Port": "1234",
        },
        params={"limit": 10, "offset": 20},
    )
    data = await json_body(response)
    assert len(data) == 0
    link = response.headers["Link"]
    assert link == (
        '<https://whenbeer.pub:1234/tasks?limit=10&offset=0>; rel="first", '
        '<https://whenbeer.pub:1234/tasks?limit=10&offset=10>; rel="prev"'
    )
    assert response.headers["X-total-count"] == "2"
    #
    response = await cli.get(
        "/tasks",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "whenbeer.pub",
            "X-Forwarded-Port": "443",
        },
        params={"limit": 10, "offset": 20},
    )
    data = await json_body(response)
    assert len(data) == 0
    link = response.headers["Link"]
    assert link == (
        '<https://whenbeer.pub/tasks?limit=10&offset=0>; rel="first", '
        '<https://whenbeer.pub/tasks?limit=10&offset=10>; rel="prev"'
    )
    assert response.headers["X-total-count"] == "2"


async def test_direction_asc(cli2, series):
    assert await direction_asc(cli2, series, "/series_offset")


async def test_direction_desc(cli2, series):
    assert await direction_desc(cli2, series, "/series_offset")
