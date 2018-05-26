from aiohttp import web

from openapi.db.path import SqlApiPath
from openapi.spec import op
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
        """
        data = await self.create_one()
        return web.json_response(data, status=201)


@routes.view('/tasks/{id}')
class TaskPath(SqlApiPath):
    """
    ---
    summary: Create and query tasks
    tags:
        - task
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
