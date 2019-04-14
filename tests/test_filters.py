import pytest
from multidict import MultiDict

from openapi.spec import OpenApiSpec
from openapi.testing import jsonBody

tests = [
    {"title": "test1", "unique_title": "thefirsttest", "severity": 1},
    {"title": "test2", "unique_title": "anothertest1", "severity": 3},
    {"title": "test3"},
]


@pytest.fixture
async def fixtures(cli):
    results = []
    for test in tests:
        rs = await cli.post("/tasks", json=test)
        test = await jsonBody(rs, 201)
        test.pop("id")
        results.append(test)
    return results


async def assert_query(cli, params, expected):
    response = await cli.get("/tasks", params=params)
    body = await jsonBody(response, 200)
    for d in body:
        d.pop("id")
    assert body == expected


async def test_spec(test_app):
    spec = OpenApiSpec()
    spec.build(test_app)
    query = spec.paths["/tasks"]["get"]["parameters"]
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
    test1, test2, test3 = fixtures
    await assert_query(cli, {"severity:gt": 1}, [test2])
    await assert_query(cli, {"severity:ge": 1}, [test1, test2])
    await assert_query(cli, {"severity:lt": 3}, [test1])
    await assert_query(cli, {"severity:le": 2}, [test1])
    await assert_query(cli, {"severity:le": 3}, [test1, test2])
    await assert_query(cli, {"severity:ne": 3}, [test1])
    await assert_query(cli, {"severity": 2}, [])
    await assert_query(cli, {"severity": 1}, [test1])
    await assert_query(cli, {"severity": "NULL"}, [test3])


async def test_multiple(cli, fixtures):
    test1, test2, test3 = fixtures
    params = MultiDict((("severity", 1), ("severity", 3)))
    await assert_query(cli, params, [test1, test2])


async def test_search(cli, fixtures):
    test1, test2, test3 = fixtures
    params = {"search": "test"}
    await assert_query(cli, params, [test1, test2, test3])


async def test_search_match_one(cli, fixtures):
    test1, test2, test3 = fixtures
    params = {"search": "est2"}
    await assert_query(cli, params, [test2])


async def test_search_match_one_with_title(cli, fixtures):
    test1, test2, test3 = fixtures
    params = {"title": "test2", "search": "est2"}
    await assert_query(cli, params, [test2])


async def test_search_match_none_with_title(cli, fixtures):
    params = {"title": "test1", "search": "est2"}
    await assert_query(cli, params, [])


async def test_search_either_end(cli, fixtures):
    test1, test2, test3 = fixtures
    params = {"search": "est"}
    await assert_query(cli, params, [test1, test2, test3])


async def test_multicolumn_search(cli, fixtures):
    test1, test2, test3 = fixtures
    params = {"search": "est1"}
    await assert_query(cli, params, [test1, test2])
