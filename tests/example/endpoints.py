from aiohttp import web

from openapi.db.path import SqlApiPath
from openapi.spec import op
from .models import Task, TaskAdd, TaskQuery


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
