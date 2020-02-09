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
- Optional sentry_ middleware


Getting Started
===============

The `app` implementation:

.. code-block:: python

    from openapi.rest import rest

    from .endpoint import TasksPath

    def create_app():
        return rest(
            openapi=dict(
                title='A REST API',
                ...
            ),
            base_path='/v1',
            allowed_tags=[...],
            validate_docs=True,
            setup_app=setup_app,
            commands=[...]
        )


    def setup_app(app):
        app.router.add_routes(TasksPath)
        return app


    if __name__ == '__main__':
        create_app().main()


The `endpoint` implementation:

.. code-block:: python

    from typing import List

    from aiohttp import web

    from openapi.db.path import SqlApiPath
    from openapi.spec import op


    routes = web.RouteTableDef()


    @routes.view('/tasks')
    class TasksPath(SqlApiPath):
        """
        ---
        summary: Create and query Tasks
        tags:
            - name: Task
              description: Task tag description
        """
        table = 'tasks'

        @op(query_schema=TaskOrderableQuery, response_schema=List[Task])
        async def get(self) -> web.Response:
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
        async def post(self) -> web.Response:
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

Contents
========

.. toctree::
   :maxdepth: 2

   reference
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
