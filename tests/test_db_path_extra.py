from datetime import datetime
from uuid import UUID

from openapi.testing import jsonBody


async def test_get_update(cli):
    response = await cli.post('/tasks', json=dict(title='test task2 2'))
    data = await jsonBody(response, 201)
    id_ = UUID(data['id'])
    task_path = f'/tasks2/{id_.hex}'

    assert data['title'] == 'test task2 2'
    #
    # now get it
    response = await cli.get(task_path)
    data = await jsonBody(response, 200)
    assert data['title'] == 'test task2 2'
    #
    # now update
    response = await cli.patch(
        task_path, json=dict(done=datetime.now().isoformat())
    )
    data = await jsonBody(response, 200)
    assert data['id'] == id_.hex
    #
    # now delete it
    response = await cli.delete(task_path)
    assert response.status == 204
    response = await cli.delete(task_path)
    await jsonBody(response, 404)
