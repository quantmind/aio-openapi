from aiohttp import web

from sqlalchemy.sql.expression import null

from openapi.db.path import SqlApiPath
from openapi.spec import op
from openapi.exc import JsonHttpException
from .models import Task, TaskAdd, TaskQuery, TaskPathSchema, TaskUpdate


routes = web.RouteTableDef()


@routes.view('/tasks')
class TasksPath(SqlApiPath):
    """
    ---
    summary: Create and query tasks
    tags:
        - task
    """
    table = 'tasks'

    def filter_done(self, op, value):
        done = self.db_table.c.done
        return done != null() if value else done == null()

    @op(query_schema=TaskQuery, response_schema=[Task])
    async def get(self):
        """
        ---
        summary: retrieve a list of tasks
        responses:
            200:
                description: Authenticated tasks
        """
        data = await self.get_list()
        return web.json_response(data)

    @op(response_schema=Task, body_schema=TaskAdd)
    async def post(self):
        """
        ---
        summary: create a new task
        responses:
            201:
                description: the task was successfully added
            422:
                description: Failed validation
        """
        data = await self.create_one()
        return web.json_response(data, status=201)

    @op(query_schema=TaskQuery)
    async def delete(self):
        """
        ---
        summary: Delete a group of tasks
        responses:
            204:
                description: Tasks successfully deleted
        """
        await self.delete_list(query=dict(self.request.query))
        return web.Response(status=204)


@routes.view('/tasks/{id}')
class TaskPath(SqlApiPath):
    """
    ---
    summary: Create and query tasks
    tags:
        - name: task
          description: simple description
        - name: random
    """
    table = 'tasks'
    path_schema = TaskPathSchema

    @op(response_schema=Task)
    async def get(self):
        """
        ---
        summary: get an existing Task by ID
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
        summary: update an existing Task by ID
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
        summary: Delete an existing task
        responses:
            204:
                description: Task successfully deleted
        """
        await self.delete_one()
        return web.Response(status=204)


@routes.view('/bulk/tasks')
class TaskBulkPath(SqlApiPath):
    """
    summary: Bulk manage tasks
    tags:
        - task
    """
    table = 'tasks'

    @op(body_schema=[TaskAdd], response_schema=[Task])
    async def post(self):
        """
        ---
        summary: bulk create tasks
        responses:
            201:
                description: created tasks
        """
        data = await self.create_list()
        return self.json_response(data, status=201)


@routes.view('/transaction/tasks')
class TaskTransactionsPath(SqlApiPath):
    """
    summary: Manage tasks with transactions
    tags:
        - task
        - transaction
    """
    table = 'tasks'

    @op(body_schema=TaskAdd, response_schema=Task)
    async def post(self):
        data = await self.json_data()
        async with self.db.acquire() as conn:
            async with conn.transaction():
                should_raise = data.pop('should_raise', False)

                task = await self.create_one(data=data, conn=conn)

                if should_raise:
                    raise JsonHttpException(status=500)

                return self.json_response(data=task, status=201)

    @op(query_schema=TaskQuery, response_schema=[Task])
    async def get(self):
        """
        ---
        summary: retrieve a list of tasks
        responses:
            200:
                description: Authenticated tasks
        """
        async with self.db.acquire() as conn:
            data = await self.get_list(conn=conn)
            return self.json_response(data=data)


@routes.view('/transaction/tasks/{id}')
class TaskTransactionPath(SqlApiPath):
    """
    summary: Manage tasks with transactions
    tags:
        - task
        - transaction
    """
    table = 'tasks'
    path_schema = TaskPathSchema

    @op(response_schema=Task)
    async def get(self):
        """
        ---
        summary: get an existing Task by ID
        responses:
            200:
                description: the task
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                data = await self.get_one(conn=conn)
                return self.json_response(data)

    @op(body_schema=TaskUpdate, response_schema=Task)
    async def patch(self):
        """
        ---
        summary: update an existing Task by ID
        responses:
            200:
                description: the updated task
        """
        data = await self.json_data()
        async with self.db.acquire() as conn:
            async with conn.transaction():
                should_raise = data.pop('should_raise', False)

                task = await self.update_one(data=data, conn=conn)

                if should_raise:
                    raise JsonHttpException(status=500)

                return self.json_response(data=task, status=200)

    @op()
    async def delete(self):
        """
        ---
        summary: Delete an existing task
        responses:
            204:
                description: Task successfully deleted
        """
        data = await self.json_data()
        async with self.db.acquire() as conn:
            async with conn.transaction():
                should_raise = data.pop('should_raise', False)

                await self.delete_one(conn=conn)

                if should_raise:
                    raise JsonHttpException(status=500)

                return self.json_response(data={}, status=204)


@routes.view('/transaction/bulk/tasks')
class TaskBulkTransactionPath(SqlApiPath):
    """
    summary: Bulk manage tasks with transactions
    tags:
        - task
        - transaction
    """
    table = 'tasks'

    @op(query_schema=TaskQuery)
    async def delete(self):
        """
        ---
        summary: Delete a group of tasks
        responses:
            204:
                description: Tasks successfully deleted
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                await self.delete_list(
                    query=dict(self.request.query), conn=conn
                )
                return web.Response(status=204)

    @op(body_schema=[TaskAdd], response_schema=[Task])
    async def post(self):
        """
        ---
        summary: bulk create tasks
        responses:
            201:
                description: created tasks
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                data = await self.create_list(conn=conn)
                return self.json_response(data, status=201)
