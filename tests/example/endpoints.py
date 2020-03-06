from typing import List

from aiohttp import web
from sqlalchemy.sql.expression import null

from openapi.db.path import SqlApiPath
from openapi.spec import op

from .models import (
    Task,
    TaskAdd,
    TaskOrderableQuery,
    TaskPathSchema,
    TaskQuery,
    TaskUpdate,
)

routes = web.RouteTableDef()


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

    @op(query_schema=TaskOrderableQuery, response_schema=List[Task])
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
