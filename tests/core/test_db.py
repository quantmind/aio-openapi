import uuid
from asyncio import TimeoutError
from datetime import datetime
from decimal import Decimal

import async_timeout

from openapi.db import CrudDB
from openapi.json import dumps
from openapi.testing import json_body
from openapi.utils import error_dict


def test_drop_all(db: CrudDB):
    db.drop_all()


async def test_get_list(cli):
    response = await cli.get("/tasks")
    data = await json_body(response)
    assert len(data) == 0


async def test_get_404(cli):
    response = await cli.get("/tasks/101")
    await json_body(response, 404)
    response = await cli.get("/tasks/bla")
    await json_body(response, 404)
    response = await cli.patch("/tasks/101", json=dict(title="ciao"))
    await json_body(response, 404)
    response = await cli.patch("/tasks/bla", json=dict(title="ciao"))
    await json_body(response, 404)


async def test_400(cli):
    response = await cli.patch("/tasks/101")
    await json_body(response, 400)


async def test_create(cli):
    response = await cli.post("/tasks", json=dict(title="test 1", type="todo"))
    data = await json_body(response, 201)

    uuid.UUID(data["id"])  # Check that we get a valid uuid
    assert data["title"] == "test 1"
    assert data["type"] == "todo"


async def test_create_422(cli):
    response = await cli.post("/tasks", json=dict(severity=4))
    data = await json_body(response, 422)
    assert len(data["errors"]) == 1
    errors = error_dict(data["errors"])
    assert errors["title"] == "required"


async def test_get_update(cli):
    response = await cli.post("/tasks", json=dict(title="test 2"))
    data = await json_body(response, 201)

    task_id = uuid.UUID(data["id"])  # Check that we get a valid uuid
    assert data["title"] == "test 2"
    #
    # now get it
    task_path = f"/tasks/{task_id.hex}"
    response = await cli.get(task_path)
    await json_body(response, 200)
    #
    # now update
    response = await cli.patch(task_path, json=dict(done=datetime.now().isoformat()))
    data = await json_body(response, 200)
    assert data["id"] == task_id.hex
    #
    # now delete it
    response = await cli.delete(task_path)
    assert response.status == 204
    response = await cli.get(task_path)
    await json_body(response, 404)


async def test_update_empty(cli):
    response = await cli.post("/tasks", json=dict(title="U2", story_points=5))
    data = await json_body(response, 201)
    id_ = data["id"]
    response = await cli.patch(f"/tasks/{id_}", json={})
    data2 = await json_body(response, 200)
    assert data == data2


async def test_delete_list(cli):
    response = await cli.delete("/tasks")
    assert response.status == 204
    response = await cli.post("/tasks", json=dict(title="bla"))
    d1 = await json_body(response, 201)
    response = await cli.post("/tasks", json=dict(title="foo"))
    d2 = await json_body(response, 201)
    assert d1 != d2
    response = await cli.get("/tasks")
    data = await json_body(response)
    assert len(data) == 2
    await cli.patch(
        f'/tasks/{data[0]["id"]}', json=dict(done=datetime.now().isoformat())
    )
    response = await cli.get("/tasks", params={"done": "true"})
    data = await json_body(response)
    assert len(data) == 1
    assert data[0]["done"]
    response = await cli.delete("/tasks", params={"done": "true"})
    assert response.status == 204
    response = await cli.get("/tasks")
    data = await json_body(response)
    assert len(data) == 1
    assert "done" not in data[0]


async def test_create_list(cli):
    tasks = [dict(title="foo"), dict(title="bar")]
    response = await cli.post("/bulk/tasks", json=tasks)
    data = await json_body(response, status=201)
    titles = list(map(lambda t: t["title"], data))
    assert len(titles) == 2
    assert "foo" in titles
    assert "bar" in titles


async def test_get_ordered_list(cli):
    tasks = [dict(title="c"), dict(title="a"), dict(title="b")]
    response = await cli.post("/bulk/tasks", json=tasks)
    await json_body(response, status=201)

    response = await cli.get("/tasks?order_by=title")
    data = await json_body(response, 200)
    titles = list(map(lambda t: t["title"], data))
    assert titles == ["a", "b", "c"]


async def test_get_ordered_list_desc(cli):
    tasks = [dict(title="c"), dict(title="a"), dict(title="b")]
    response = await cli.post("/bulk/tasks", json=tasks)
    await json_body(response, status=201)

    response = await cli.get("/tasks?order_by=title&order_desc=true")
    data = await json_body(response, 200)
    titles = list(map(lambda t: t["title"], data))
    assert titles == ["c", "b", "a"]


async def test_limit_list(cli):
    tasks = [dict(title="c"), dict(title="a"), dict(title="b")]
    response = await cli.post("/bulk/tasks", json=tasks)
    await json_body(response, status=201)

    params = {"order_by": "title", "limit": 2}
    response = await cli.get("/tasks", params=params)
    data = await json_body(response, 200)
    titles = list(map(lambda t: t["title"], data))
    assert len(titles) == 2
    assert titles == ["a", "b"]


async def test_limit_and_offset_list(cli):
    tasks = [dict(title="c"), dict(title="a"), dict(title="b")]
    response = await cli.post("/bulk/tasks", json=tasks)
    await json_body(response, status=201)

    params = {"order_by": "title", "limit": 2, "offset": 1}
    response = await cli.get("/tasks", params=params)
    data = await json_body(response, 200)
    titles = list(map(lambda t: t["title"], data))
    assert len(titles) == 2
    assert titles == ["b", "c"]


async def test_validation_error_if_field_not_allowed(cli):
    tasks = [dict(title="c"), dict(title="a"), dict(title="b")]
    response = await cli.post("/bulk/tasks", json=tasks)
    await json_body(response, status=201)

    response = await cli.get("/tasks?order_by=done")
    await json_body(response, 422)


async def test_transaction_create(cli):
    response = await cli.post("/transaction/tasks", json=dict(title="tran"))
    data = await json_body(response, status=201)
    assert data["title"] == "tran"


async def test_transaction_create_error(cli):
    response_tasks_before = await cli.get("/transaction/tasks")
    tasks_before = await json_body(response_tasks_before)
    response = await cli.post(
        "/transaction/tasks", json=dict(title="tran", should_raise=True)
    )
    await json_body(response, status=500)
    response_tasks_after = await cli.get("/transaction/tasks")
    tasks_after = await json_body(response_tasks_after)
    assert len(tasks_before) == len(tasks_after)


async def test_transaction_update(cli):
    response = await cli.post("/tasks", json=dict(title="tran"))
    task = await json_body(response, status=201)
    response = await cli.patch(
        f'/transaction/tasks/{task["id"]}', json=dict(title="newtask")
    )
    data = await json_body(response)
    assert data["title"] == "newtask"


async def test_transaction_update_error(cli):
    response = await cli.post("/tasks", json=dict(title="tran"))
    task = await json_body(response, status=201)
    response = await cli.patch(
        f'/transaction/tasks/{task["id"]}',
        json=dict(title="newtask", should_raise=True),
    )
    await json_body(response, status=500)
    response = await cli.get(f'/transaction/tasks/{task["id"]}')
    data = await json_body(response)
    assert data["title"] == "tran"


async def test_transaction_delete(cli):
    response = await cli.post("/tasks", json=dict(title="tran"))
    task = await json_body(response, status=201)
    response = await cli.delete(f'/transaction/tasks/{task["id"]}', json={})
    await json_body(response, status=204)
    response = await cli.get(f'/transaction/tasks/{task["id"]}')
    await json_body(response, status=404)


async def test_transaction_delete_error(cli):
    response = await cli.post("/tasks", json=dict(title="tran"))
    task = await json_body(response, status=201)
    response = await cli.delete(
        f'/transaction/tasks/{task["id"]}', json=dict(should_raise=True)
    )
    await json_body(response, status=500)
    response = await cli.get(f'/tasks/{task["id"]}')
    await json_body(response, 200)


async def test_transaction_get_list(cli):
    await cli.post("/tasks", json=dict(title="tran"))
    await cli.post("/tasks", json=dict(title="tran"))
    await cli.post("/tasks", json=dict(title="tran"))
    response = await cli.get("/transaction/tasks")
    await json_body(response)


async def test_transaction_create_list(cli):
    tasks = [dict(title="foo"), dict(title="bar")]
    response = await cli.post("/transaction/bulk/tasks", json=tasks)
    data = await json_body(response, status=201)
    titles = list(map(lambda t: t["title"], data))
    assert len(titles) == 2
    assert "foo" in titles
    assert "bar" in titles


async def test_transaction_delete_list(cli):
    response = await cli.delete("/transaction/bulk/tasks")
    assert response.status == 204
    tasks = [dict(title="bulk_created") for i in range(5)]
    response = await cli.post("/transaction/bulk/tasks", json=tasks)
    data = await json_body(response, 201)
    assert len(data) == 5

    response = await cli.delete(
        "/transaction/bulk/tasks", json=dict(title="bulk_created")
    )
    assert response.status == 204

    response = await cli.get("/transaction/tasks", params={"title": "bulk_created"})
    data = await json_body(response)

    assert len(data) == 0


async def test_create_unique_error(cli):
    task = {"title": "task", "unique_title": "task"}
    response = await cli.post("/tasks", json=task)
    await json_body(response, status=201)

    duplicated_response = await cli.post("/tasks", json=task)
    duplicated_body = await json_body(duplicated_response, status=422)
    assert duplicated_body["message"] == "unique_title already exists"


async def test_update_unique_error(cli):
    task1 = {"title": "task", "unique_title": "task1"}
    task2 = {"title": "task", "unique_title": "task2"}
    response1 = await cli.post("/tasks", json=task1)
    await json_body(response1, status=201)
    response2 = await cli.post("/tasks", json=task2)
    task_body = await json_body(response2, status=201)

    duplicated_response = await cli.patch(f'/tasks/{task_body["id"]}', json=task1)
    duplicated_body = await json_body(duplicated_response, status=422)
    assert duplicated_body["message"] == "unique_title already exists"


async def test_decimal_zero_returned(cli):
    task = {"title": "task", "unique_title": "task1", "story_points": Decimal(0)}
    resp = await cli.post("/tasks", data=dumps(task))
    body = await json_body(resp, status=201)

    assert "story_points" in body

    get_resp = await cli.get(f"/tasks/{body['id']}")
    get_body = await json_body(get_resp, status=200)

    assert get_body["story_points"] == Decimal(0)


async def test_multicolumn_unique_constraint(cli):
    row = {"x": 1, "y": 2}
    resp = await cli.post("/multikey-unique", json=row)
    await json_body(resp, status=201)

    resp = await cli.post("/multikey-unique", json=row)
    await json_body(resp, status=422)


async def test_json_column_with_decimals(cli):
    task = {"title": "task", "unique_title": "task1", "story_points": Decimal(0)}
    resp = await cli.post("/tasks", data=dumps(task))
    await json_body(resp, status=201)


async def test_db_ensure_connection(db: CrudDB):
    async with db.connection() as conn:
        assert not conn.in_transaction()
        async with db.ensure_connection(conn=conn) as conn2:
            assert conn is conn2
            assert conn.in_transaction()


def test_db_props(db: CrudDB):
    assert db.dsn == str(db)


async def test_db_pool(db: CrudDB):
    async with db.connection():
        try:
            async with async_timeout.timeout(0.5):
                async with db.connection() as conn2:
                    assert not conn2
        except TimeoutError:
            pass
