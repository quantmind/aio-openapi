from datetime import datetime
from openapi.testing import jsonBody


async def test_get_update(cli):
    response = await cli.post('/tasks', json=dict(title='test task2 2'))
    data = await jsonBody(response, 201)
    id_ = data['id']
    assert data['title'] == 'test task2 2'
    #
    # now get it
    response = await cli.get(f'/tasks2/{id_}')
    data = await jsonBody(response, 200)
    assert data['title'] == 'test task2 2'
    #
    # now update
    response = await cli.patch(
        f'/tasks2/{id_}', json=dict(done=datetime.now().isoformat())
    )
    data = await jsonBody(response, 200)
    assert data['id'] == id_
    #
    # now delete it
    response = await cli.delete(f'/tasks2/{id_}')
    assert response.status == 204
    response = await cli.delete(f'/tasks2/{id_}')
    await jsonBody(response, 404)
