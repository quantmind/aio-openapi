import pytest
from multidict import MultiDict

from openapi.spec import OpenApiSpec
from openapi.testing import json_body
from tests.utils import FakeRequest

tests = [
    {"title": "test1", "unique_title": "thefirsttest", "severity": 1},
    {"title": "test2", "unique_title": "anothertest1", "severity": 3},
    {"title": "test3"},
    {"title": "test4", "unique_title": "anothertest4", "severity": 5},
]


@pytest.fixture
async def fixtures(cli):
    results = []
    for test in tests:
        rs = await cli.post("/tasks", json=test)
        test = await json_body(rs, 201)
        test.pop("id")
        results.append(test)
    return results


async def assert_query(cli, params, expected):
    response = await cli.get("/tasks", params=params)
    data = await json_body(response)
    for d in data:
        d.pop("id")
    assert len(data) == len(expected)
    assert data == expected


async def test_spec(test_app):
    spec = OpenApiSpec()
    doc = spec.build(FakeRequest.from_app(test_app))
    query = doc["paths"]["/tasks"]["get"]["parameters"]
    filters = [q["name"] for q in query]
    assert set(filters) == {
        "title",
        "done",
        "type",
        "search",
        "severity",
        "severity:lt",
        "severity:le",
        "severity:gt",
        "severity:ge",
        "severity:ne",
        "story_points",
        "order_by",
        "order_desc",
        "limit",
        "offset",
    }


async def test_filters(cli, fixtures):
    test1, test2, test3, test4 = fixtures
    await assert_query(cli, {"severity:gt": 1}, [test2, test4])
    await assert_query(cli, {"severity:ge": 1}, [test1, test2, test4])
    await assert_query(cli, {"severity:lt": 3}, [test1])
    await assert_query(cli, {"severity:le": 2}, [test1])
    await assert_query(cli, {"severity:le": 3}, [test1, test2])
    await assert_query(cli, {"severity:ne": 3}, [test1, test4])
    await assert_query(cli, {"severity": 2}, [])
    await assert_query(cli, {"severity": 1}, [test1])
    await assert_query(cli, {"severity": "NULL"}, [test3])


async def test_multiple(cli, fixtures):
    test1, test2, test3, test4 = fixtures
    params = MultiDict((("severity", 1), ("severity", 3)))
    await assert_query(cli, params, [test1, test2])
    params = MultiDict((("severity:ne", 1), ("severity:ne", 3)))
    await assert_query(cli, params, [test4])


async def test_search(cli, fixtures):
    test1, test2, test3, test4 = fixtures
    params = {"search": "test"}
    await assert_query(cli, params, [test1, test2, test3, test4])


async def test_search_match_one(cli, fixtures):
    test2 = fixtures[1]
    params = {"search": "est2"}
    await assert_query(cli, params, [test2])


async def test_search_match_one_with_title(cli, fixtures):
    test2 = fixtures[1]
    params = {"title": "test2", "search": "est2"}
    await assert_query(cli, params, [test2])


async def test_search_match_none_with_title(cli, fixtures):
    params = {"title": "test1", "search": "est2"}
    await assert_query(cli, params, [])


async def test_search_either_end(cli, fixtures):
    params = {"search": "est"}
    await assert_query(cli, params, fixtures)


async def test_multicolumn_search(cli, fixtures):
    test1, test2, test3, _ = fixtures
    params = {"search": "est1"}
    await assert_query(cli, params, [test1, test2])
