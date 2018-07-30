from dataclasses import asdict

from openapi.spec import OpenApi, OpenApiSpec
from openapi.testing import jsonBody


async def test_spec(test_app):
    open_api = OpenApi()

    spec = OpenApiSpec(asdict(open_api))
    spec.build(test_app)
    query = spec.paths['/tasks']['get']['parameters']
    filters = [q['name'] for q in query]
    assert set(filters) == {
        'done',
        'type',
        'severity',
        'severity:lt',
        'severity:le',
        'severity:gt',
        'severity:ge',
        'severity:ne',
    }


async def test_filters(cli, clean_db):
    tests = [{
            'title': 'test1',
            'severity': 1
        },
        {
            'title': 'test2',
            'severity': 3
        },
        {
            'title': 'test3'
        }
    ]

    results = []
    for test in tests:
        rs = await cli.post('/tasks', json=test)
        test = await jsonBody(rs, 201)
        test.pop('id')
        results.append(test)

    async def assert_query(params, expected):
        response = await cli.get('/tasks', params=params)
        body = await jsonBody(response, 200)
        for d in body:
            d.pop('id')
        assert body == expected

    test1, test2, test3 = results
    await assert_query({'severity:gt': 1}, [test2])
    await assert_query({'severity:ge': 1}, [test1, test2])
    await assert_query({'severity:lt': 3}, [test1])
    await assert_query({'severity:le': 2}, [test1])
    await assert_query({'severity:le': 3}, [test1, test2])
    await assert_query({'severity:ne': 3}, [test1])
    await assert_query({'severity': 2}, [])
    await assert_query({'severity': 1}, [test1])
    await assert_query({'severity': 'NULL'}, [test3])
