from dataclasses import asdict

from openapi.spec import OpenApi, OpenApiSpec
from openapi.testing import jsonBody


async def test_spec(test_app):
    open_api = OpenApi()

    spec = OpenApiSpec(asdict(open_api))
    spec.build(test_app)
    assert spec.schemas['TaskQuery']['properties'].keys() == {
        'done',
        'severity',
        'severity:lt',
        'severity:le',
        'severity:gt',
        'severity:ge',
        'severity:ne',
    }


async def test_filters(cli, clean_db):
    test1 = {
        'title': 'test1',
        'severity': 1
    }
    test2 = {
        'title': 'test2',
        'severity': 3
    }
    test3 = {
        'title': 'test3'
    }

    await cli.post('/tasks', json=test1)
    await cli.post('/tasks', json=test2)
    await cli.post('/tasks', json=test3)

    async def assert_query(params, expected):
        response = await cli.get('/tasks', params=params)
        body = await jsonBody(response, 200)
        for d in body:
            d.pop('id')
        assert body == expected

    await assert_query({'severity:gt': 1}, [test2])
    await assert_query({'severity:ge': 1}, [test1, test2])
    await assert_query({'severity:lt': 3}, [test1])
    await assert_query({'severity:le': 2}, [test1])
    await assert_query({'severity:le': 3}, [test1, test2])
    await assert_query({'severity:ne': 3}, [test1])
    await assert_query({'severity': 2}, [])
    await assert_query({'severity': 1}, [test1])
    await assert_query({'severity': 'NULL'}, [test3])
