from aiohttp import web
from sqlalchemy.sql.expression import null

from openapi.db.path import SqlApiPath
from openapi.exc import JsonHttpException
from openapi.spec import op

from .models import (
    MultiKey,
    Task,
    TaskAdd,
    TaskOrderableQuery,
    TaskPathSchema,
    TaskPathSchema2,
    TaskQuery,
    TaskUpdate,
)

routes = web.RouteTableDef()
invalid_path_routes = web.RouteTableDef()
invalid_method_description_routes = web.RouteTableDef()
invalid_method_summary_routes = web.RouteTableDef()
invalid_method_description_routes = web.RouteTableDef()
invalid_tag_missing_description_routes = web.RouteTableDef()


@routes.get("/status")
async def status(request):
    return web.json_response({})


@routes.get("/error")
async def error(request):
    1 / 0  # noqa


@routes.view("/tasks")
class TasksPath(SqlApiPath):
    """
    ---
    summary: Create and query Tasks
    tags:
        - Task
    """

    table = "tasks"

    def filter_done(self, op, value):
        done = self.db_table.c.done
        return done != null() if value else done == null()

    @op(query_schema=TaskOrderableQuery, response_schema=[Task])
    async def get(self):
        """
        ---
        summary: Retrieve Tasks
        description: Retrieve a list of Tasks
        responses:
            200:
                description: Authenticated tasks
        """
        paginated = await self.get_list()
        return paginated.json_response()

    @op(response_schema=Task, body_schema=TaskAdd)
    async def post(self):
        """
        ---
        summary: Create a Task
        description: Create a new Task
        responses:
            201:
                description: the task was successfully added
            422:
                description: Failed validation
        """
        data = await self.create_one()
        return self.json_response(data, status=201)

    @op(query_schema=TaskQuery)
    async def delete(self):
        """
        ---
        summary: Delete Tasks
        description: Delete a group of Tasks
        responses:
            204:
                description: Tasks successfully deleted
        """
        await self.delete_list(query=dict(self.request.query))
        return web.Response(status=204)


@routes.view("/tasks/{id}")
class TaskPath(SqlApiPath):
    """
    ---
    summary: Create and query tasks
    tags:
        - name: Task
          description: Simple description
        - name: Random
          description: Random description
    """

    table = "tasks"
    path_schema = TaskPathSchema

    @op(response_schema=Task)
    async def get(self):
        """
        ---
        summary: Retrieve a Task
        description: Retrieve a Task by ID
        responses:
            200:
                description: the task
        """
        data = await self.get_one()
        return self.json_response(data)

    @op(response_schema=Task, body_schema=TaskUpdate)
    async def patch(self):
        """
        ---
        summary: Update a Task
        description: Update an existing Task by ID
        responses:
            200:
                description: the updated task
        """
        data = await self.update_one()
        return self.json_response(data)

    @op()
    async def delete(self):
        """
        ---
        summary: Delete a Task
        description: Delete an existing task
        responses:
            204:
                description: Task successfully deleted
        """
        await self.delete_one()
        return web.Response(status=204)


@routes.view("/bulk/tasks")
class TaskBulkPath(SqlApiPath):
    """
    ---
    summary: Bulk manage tasks
    tags:
        - Task
    """

    table = "tasks"

    @op(body_schema=[TaskAdd], response_schema=[Task])
    async def post(self):
        """
        ---
        summary: Create Tasks
        description: Create a group of Tasks
        responses:
            201:
                description: Created tasks
        """
        data = await self.create_list()
        return self.json_response(data, status=201)


@routes.view("/transaction/tasks")
class TaskTransactionsPath(SqlApiPath):
    """
    ---
    summary: Manage tasks with transactions
    tags:
        - Task
        - name: Transaction
          description: Endpoints that creates a new transaction
    """

    table = "tasks"

    @op(body_schema=TaskAdd, response_schema=Task)
    async def post(self):
        """
        ---
        summary: Create Task
        description: Create a Task using transatcion
        responses:
            201:
                description: Created Task
            500:
                description: Forced raised error
        """
        data = await self.json_data()
        async with self.db.transaction() as conn:
            should_raise = data.pop("should_raise", False)

            task = await self.create_one(data=data, conn=conn)

            if should_raise:
                raise JsonHttpException(status=500)

            return self.json_response(data=task, status=201)

    @op(query_schema=TaskOrderableQuery, response_schema=[Task])
    async def get(self):
        """
        ---
        summary: Retrieve Tasks
        description: Retrieve a list of Tasks using transaction
        responses:
            200:
                description: Authenticated tasks
        """
        paginated = await self.get_list()
        return paginated.json_response()


@routes.view("/transaction/tasks/{id}")
class TaskTransactionPath(SqlApiPath):
    """
    ---
    summary: Manage Tasks with transactions
    tags:
        - Task
        - Transaction
    """

    table = "tasks"
    path_schema = TaskPathSchema

    @op(response_schema=Task)
    async def get(self):
        """
        ---
        summary: Retrieve Task
        description: Retrieve an existing Task by ID using transaction
        responses:
            200:
                description: the task
        """
        async with self.db.transaction() as conn:
            data = await self.get_one(conn=conn)
            return self.json_response(data)

    @op(body_schema=TaskUpdate, response_schema=Task)
    async def patch(self):
        """
        ---
        summary: Update Task
        description: Update an existing Task by ID using transaction
        responses:
            200:
                description: the updated task
        """
        data = await self.json_data()
        async with self.db.transaction() as conn:
            should_raise = data.pop("should_raise", False)

            task = await self.update_one(data=data, conn=conn)

            if should_raise:
                raise JsonHttpException(status=500)

            return self.json_response(data=task, status=200)

    @op()
    async def delete(self):
        """
        ---
        summary: Delete Task
        description: Delete an existing task using transaction
        responses:
            204:
                description: Task successfully deleted
        """
        data = await self.json_data()
        async with self.db.transaction() as conn:
            should_raise = data.pop("should_raise", False)

            await self.delete_one(conn=conn)

            if should_raise:
                raise JsonHttpException(status=500)

            return self.json_response(data={}, status=204)


@routes.view("/transaction/bulk/tasks")
class TaskBulkTransactionPath(SqlApiPath):
    """
    ---
    summary: Bulk manage tasks with transactions
    tags:
        - Task
        - Transaction
    """

    table = "tasks"

    @op(query_schema=TaskQuery)
    async def delete(self):
        """
        ---
        summary: Delete Tasks
        description: Bulk delete a group of Tasks using transaction
        responses:
            204:
                description: Tasks successfully deleted
        """
        async with self.db.transaction() as conn:
            await self.delete_list(query=dict(self.request.query), conn=conn)
            return web.Response(status=204)

    @op(body_schema=[TaskAdd], response_schema=[Task])
    async def post(self):
        """
        ---
        summary: Create Tasks
        description: Bulk create Tasks using transaction
        responses:
            201:
                description: created tasks
        """
        async with self.db.transaction() as conn:
            data = await self.create_list(conn=conn)
            return self.json_response(data, status=201)


@routes.view("/tasks2/{task_id}")
class TaskPath2(SqlApiPath):
    """
    ---
    tags:
        - Task
    """

    table = "tasks"
    path_schema = TaskPathSchema2

    def get_filters(self):
        filters = super().get_filters()
        return {"id": filters["task_id"]}

    @op(response_schema=Task)
    async def get(self):
        """
        ---
        summary: Retrieve a Task
        description: Retrieve an existing Task by ID
        responses:
            200:
                description: the task
        """
        data = await self.get_one(filters=self.get_filters())
        return self.json_response(data)

    @op(response_schema=Task, body_schema=TaskUpdate)
    async def patch(self):
        """
        ---
        summary: Update a Task
        description: Update an existing Task by ID
        responses:
            200:
                description: the updated task
        """
        data = await self.update_one(filters=self.get_filters())
        return self.json_response(data)

    @op()
    async def delete(self):
        """
        ---
        summary: Delete a Task
        description: Delete an existing Task
        responses:
            204:
                description: Task successfully deleted
        """
        await self.delete_one(filters=self.get_filters())
        return web.Response(status=204)


@invalid_path_routes.view("/tasks")
class NoTagsTaskPath(SqlApiPath):
    """
    ---
    """

    pass


@invalid_method_summary_routes.view("/tasks")
class NoSummaryMethodPath(SqlApiPath):
    """
    ---
    tags:
        - Tag
    """

    @op(response_schema=[Task])
    def get(self):
        """
        ---
        description: Valid method description
        responses:
            200:
                description: Valid response description
        """
        pass


@invalid_method_description_routes.view("/tasks")
class NoDescriptionMethodPath(SqlApiPath):
    """
    ---
    tags:
        - Tag
    """

    @op(response_schema=[Task])
    def get(self):
        """
        ---
        summary: Valid method summary
        responses:
            200:
                description: Valid response description
        """
        pass


@invalid_tag_missing_description_routes.view("/tasks")
class NoTagDescriptionPath(SqlApiPath):
    """"
    ---
    tags:
        - name: Task
          description: Simple description
        - Random
    """

    pass


@routes.view("/multikey")
class MultiKeyPath(SqlApiPath):
    """
    ---
    summary: Create rows in multikey constraint table
    tags:
        - MultiKey
    """

    table = "multi_key_unique"

    @op(response_schema=MultiKey, body_schema=MultiKey)
    async def post(self):
        """
        ---
        summary: Create row in multi-column constrained table
        responses:
            201:
                description: New row
        """
        data = await self.create_one()
        return self.json_response(data, status=201)
