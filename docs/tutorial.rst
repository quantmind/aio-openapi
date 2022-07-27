.. _aio-openapi-tutorial:

========
Tutorial
========

In this tutorial we guide you through the implementation of a minimal Rest application with a database persistence and open api documentation.

The application has the following modules

.. code-block::

    - main.py
    - db.py
    - endpoints.py
    - models.py

The `main.py` is the entrypoint of the application and has the following functions:


.. code-block:: python

    from aiohttp import web
    from openapi.rest import rest


    def create_app():
        return rest(setup_app=setup_app, ...)


    def setup_app(app: web.Application) -> None:
        ...


    if __name__ == "__main__":
        """Run the app"""
        create_app().main()

The `setup_app` function setup the aiohttp application with endpoints and middleware.
We'll fill the `setup_app` function later on in the tutorial.

Endpoints
==========

Lets add some endpoint in the `endpoints.py` module:

.. code-block:: python

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



Models
=======

The models are dataclasses which implement the validation and documentation logic, these are implemented in the `models.py` module:

.. code-block:: python

    from dataclasses import dataclass
    from datetime import datetime
    from decimal import Decimal
    from typing import Dict, List, Union

    from openapi.data import fields
    from openapi.data.db import dataclass_from_table
    from openapi.pagination import offsetPagination, searchable

    from .db import DB
    from .db.tables1 import TaskType


    @dataclass
    class TaskAdd(
        dataclass_from_table(
            "_TaskAdd", DB.tasks, required=True, default=True, exclude=("id", "done")
        )
    ):
        @classmethod
        def validate(cls, data, errors):
            """here just for coverage"""


    Task = dataclass_from_table("Task", DB.tasks)


    @dataclass
    class TaskQuery(offsetPagination("title", "-title", "severity", "-severity")):
        title: str = fields.str_field(description="Task title")
        done: bool = fields.bool_field(description="done flag")
        type: TaskType = fields.enum_field(TaskType, description="Task type")
        severity: int = fields.integer_field(
            ops=("lt", "le", "gt", "ge", "ne"), description="Task severity"
        )
        story_points: Decimal = fields.decimal_field(description="Story points")


    @dataclass
    class TaskOrderableQuery(
        TaskQuery,
        searchable("title", "unique_title"),
    ):
        pass


    @dataclass
    class TaskUpdate(TaskAdd):
        done: datetime = fields.date_time_field(description="Done timestamp")


    @dataclass
    class TaskPathSchema:
        id: str = fields.uuid_field(required=True, description="Task ID")


Database
========

The `db.py` module setup the database schema, in this tutorial, a simple table where we store Tasks.

.. code-block:: python

    import enum
    import os

    from aiohttp.web import Application

    from openapi.db import CrudDB, get_db
    import sqlalchemy as sa

    from openapi.data import fields
    from openapi.db.columns import UUIDColumn


    DATASTORE = os.getenv(
        "DATASTORE", "postgresql+asyncpg://postgres:postgres@localhost:5432/openapi"
    )


    def setup(app: Application) -> CrudDB:
        return setup_tables(get_db(app, DATASTORE))


    def setup_tables(db: CrudDB) -> CrudDB:
        sa.Table(
            "tasks",
            db.metadata,
            UUIDColumn("id", make_default=True, doc="Unique ID"),
            sa.Column(
                "title",
                sa.String(64),
                nullable=False,
                info=dict(min_length=3, data_field=title_field),
            ),
            sa.Column("done", sa.DateTime(timezone=True)),
            sa.Column("severity", sa.Integer),
            sa.Column("created_by", sa.String, default="", nullable=False),
            sa.Column("type", sa.Enum(TaskType)),
            sa.Column("unique_title", sa.String, unique=True),
            sa.Column("story_points", sa.Numeric),
            sa.Column("random", sa.String(64)),
            sa.Column(
                "subtitle",
                sa.String(64),
                nullable=False,
                default="",
            ),
        )
        return db


    # this global definition is used by the dataclass_from_table function only
    DB = setup_tables(CrudDB(DATASTORE))


Open API
=========

By default, no openapi tooling is used when creating a rest application. To enable openapi auto-documenation
pass the ``openapi`` entry:


.. code-block:: python

    from openapi.rest import rest
    from openapi.spec import Redoc

     def create_app():
        return rest(
            openapi=dict(
                title="My API",
                description="My Api ...",
                version="1.0.0",
            ),
            redoc=Redoc(),
            setup_app=setup_app
        )

The :class:`.Redoc` adds a path for serving the HTML version of the openapi specification.


The main module
=================

Finally, we can put things together

.. code-block:: python

    from aiohttp import web
    from openapi.rest import rest
    from openapi.middleware import json_error

    from . import endpoints, db


    def create_app():
        return rest(
            openapi=dict(
                title="My API",
                description="My Api ...",
                version="1.0.0",
            ),
            redoc=Redoc(),
            setup_app=setup_app
        )


    def setup_app(app: web.Application) -> None:
        db.setup(app)
        app.middlewares.append(json_error())
        app.router.add_routes(endpoints.routes)


    if __name__ == "__main__":
        """Run the app"""
        create_app().main()
