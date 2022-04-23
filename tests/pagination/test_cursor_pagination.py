import pytest

from openapi.pagination import cursorPagination
from openapi.pagination.cursor import encode_cursor
from openapi.testing import json_body

from .utils import direction_asc, direction_desc


async def test_direction_asc(cli2, series):
    assert await direction_asc(cli2, series, "/series_cursor")


async def test_direction_desc(cli2, series):
    assert await direction_desc(cli2, series, "/series_cursor", direction="desc")


async def test_bad_cursor(cli2):
    response = await cli2.get("/series_cursor", params={"_cursor": "wtf"})
    assert await json_body(response, 422) == dict(message="invalid cursor")
    response = await cli2.get(
        "/series_cursor", params={"_cursor": encode_cursor([3, 4])}
    )
    assert await json_body(response, 422) == dict(message="invalid cursor")
    response = await cli2.get("/series_cursor", params={"_cursor": encode_cursor([3])})
    assert await json_body(response, 422) == dict(message="invalid cursor")


def test_cursor_pagination_error():
    with pytest.raises(ValueError):
        cursorPagination()
