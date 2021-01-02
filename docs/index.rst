.. aio-openapi

======================
Welcome to aio-openapi
======================

Asynchronous web middleware for aiohttp_ and serving Rest APIs with OpenAPI_ v 3
specification and with optional PostgreSql database bindings.

Current version is |release|.

Installation
============

It requires python 3.6 or above.

.. code-block:: bash

    pip install aio-openapi

Development
===========

Clone the repository and create a virtual environment `venv`.

Install dependencies by running the install script

.. code-block:: bash

    ./dev/install

To run tests

.. code-block:: bash

    pytest --cov


Features
========

- Asynchronous web routes with aiohttp_
- Data validation, serialization and unserialization with python :term:`dataclasses`
- OpenApi_ v 3 auto documentation
- SqlAlchemy_ expression language
- Asynchronous DB interaction with asyncpg_
- Migrations with alembic_
- SqlAlchemy tables as python dataclasses
- Support click_ command line interface
- Redoc_ document rendering (like https://api.metablock.io/v1/docs)
- Optional sentry_ middleware


Getting Started
===============

The `main` implementation:

.. code-block:: python

    import uuid

    from aiohttp import web

    from openapi import sentry
    from openapi.db import get_db
    from openapi.middleware import json_error
    from openapi.spec import Redoc
    from openapi.rest import rest

    from .db import meta
    from .endpoints import routes
    from .ws import ws_routes


    def create_app():
        return rest(redoc=Redoc(), setup_app=setup_app)


    def setup_app(app: web.Application) -> None:
        db = get_db(app)
        meta(db.metadata)
        app.middlewares.append(json_error())
        app.middlewares.append(
            sentry.middleware(app, f"https://{uuid.uuid4().hex}@sentry.io/1234567", "test")
        )
        app.router.add_routes(routes)


    if __name__ == "__main__":
        create_app().main()



The `endpoint` implementation:

.. code-block:: python

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
        TaskUpdate
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


The data `model` implementation

.. code-block:: python


Contents
========

.. toctree::
   :maxdepth: 2

   tutorial
   reference
   validation
   queries
   websocket
   env
   glossary


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _aiohttp: https://github.com/aio-libs/aiohttp
.. _OpenApi: https://www.openapis.org/
.. _sentry: https://sentry.io
.. _click: https://github.com/pallets/click
.. _SqlAlchemy: https://www.sqlalchemy.org/
.. _alembic: http://alembic.zzzcomputing.com/en/latest/
.. _asyncpg: https://github.com/MagicStack/asyncpg
.. _Redoc: https://github.com/Redocly/redoc
