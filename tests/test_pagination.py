from yarl import URL
from openapi.testing import jsonBody
from openapi.spec.pagination import Pagination


def test_last_link():
    pag = Pagination(URL('http://test.com/path?a=2&b=3'))
    #
    links = pag.links(0, 25, 0)
    assert links == {}
    #
    links = pag.links(120, 25, 0)
    assert len(links) == 2
    assert links['next']
    assert links['last']
    assert links['next'].query['offset'] == '25'
    assert links['next'].query['limit'] == '25'
    assert links['last'].query['offset'] == '100'
    assert links['last'].query['limit'] == '25'
    #
    links = pag.links(120, 25, 75)
    assert len(links) == 3
    assert links['first'].query['offset'] == '0'
    assert links['prev'].query['offset'] == '50'
    assert links['last'].query['offset'] == '100'
    #
    links = pag.links(120, 25, 50)
    assert len(links) == 4
    assert links['first'].query['offset'] == '0'
    assert links['prev'].query['offset'] == '25'
    assert links['next'].query['offset'] == '75'
    assert links['last'].query['offset'] == '100'


async def test_pagination_next_link(cli):
    response = await cli.post('/tasks', json=dict(title='bla'))
    await jsonBody(response, 201)
    response = await cli.post('/tasks', json=dict(title='foo'))
    await jsonBody(response, 201)
    response = await cli.get('/tasks')
    data = await jsonBody(response)
    assert 'Link' not in response.headers
    assert len(data) == 2


async def test_pagination_prev_and_next_link(cli):
    response = await cli.post('/tasks', json=dict(title='bla'))
    await jsonBody(response, 201)
    response = await cli.post('/tasks', json=dict(title='foo'))
    await jsonBody(response, 201)
    response = await cli.get(
        '/tasks',
        params={'limit': 10, 'offset': 20}
    )
    url = response.url
    data = await jsonBody(response)
    assert response.headers['Link'] == (
        f'<{url.parent}{url.path}?limit=10&offset=0> rel="first", '
        f'<{url.parent}{url.path}?limit=10&offset=10> rel="prev"'
    )
    assert 'Link' in response.headers
    assert len(data) == 0
