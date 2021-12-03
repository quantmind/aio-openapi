# aio-openapi

[![PyPI version](https://badge.fury.io/py/aio-openapi.svg)](https://badge.fury.io/py/aio-openapi)
[![Python versions](https://img.shields.io/pypi/pyversions/aio-openapi.svg)](https://pypi.org/project/aio-openapi)
[![Build](https://github.com/quantmind/aio-openapi/workflows/build/badge.svg)](https://github.com/quantmind/aio-openapi/actions?query=workflow%3Abuild)
[![Coverage Status](https://coveralls.io/repos/github/quantmind/aio-openapi/badge.svg?branch=master)](https://coveralls.io/github/quantmind/aio-openapi?branch=master)
[![Documentation Status](https://readthedocs.org/projects/aio-openapi/badge/?version=latest)](https://aio-openapi.readthedocs.io/en/latest/?badge=latest)
[![Downloads](https://img.shields.io/pypi/dd/aio-openapi.svg)](https://pypi.org/project/aio-openapi/)

Asynchronous web middleware for [aiohttp][] and serving Rest APIs with [OpenAPI][] v 3
specification and with optional [PostgreSql][] database bindings.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

**Table of Contents**

- [Installation](#installation)
- [Development](#development)
- [Features](#features)
- [Web App](#web-app)
- [OpenAPI Documentation](#openapi-documentation)
- [Database Integration](#database-integration)
- [Websockets](#websockets)
  - [RPC protocol](#rpc-protocol)
  - [Publish/Subscribe](#publishsubscribe)
- [Environment Variables](#environment-variables)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Installation

```
pip install aio-openapi
```

## Development

Clone the repository and create a virtual environment `venv`.

Install dependencies by running the install script

```
make install
```

To run tests

```
make test
```

By default tests are run against a database with the following connection string `postgresql+asyncpg://postgres:postgres@localhost:5432/openapi`. To use a different DB, create a `.env` file with
a different connection string, for example:

```
DATASTORE=postgresql+asyncpg://postgres:postgres@localhost:6432/openapi
```

## Features

- Asynchronous web routes with [aiohttp](https://aiohttp.readthedocs.io/en/stable/)
- Data validation, serialization and unserialization with python [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [OpenApi][] v 3 auto documentation
- [SqlAlchemy][] expression language
- Asynchronous DB interaction with [asyncpg][]
- Migrations with [alembic][]
- SqlAlchemy tables as python dataclasses
- Support [click][] command line interface
- Optional [sentry](https://sentry.io) middleware

## Web App

To create an openapi RESTful application follow this schema (lets call the file `main.py`)

```python
from openapi.rest import rest

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
    app.router.add_routes(...)
    return app


if __name__ == '__main__':
    create_app().main()
```

The `create_app` function creates the [aiohttp][] server application by invoking the `rest` function.
This function adds the [click][] command in the `cli` mapping entry and add
documentation for routes which support OpenAPI docs.
The `setup_app` function is used to actually setup the custom application, usually by adding middleware, routes,
shutdown callbacks, database integration and so forth.

## OpenAPI Documentation

The library provide tools for creating OpenAPI v 3 compliant endpoints and
auto-document them.

An example from test `tests/example` directory

```python
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
```

## Database Integration

This library provides integration with [asyncpg][], an high performant asynchronous
connector with [PostgreSql][] database.
To add the database extension simply use the `get_db` function in the applicatiuon `setup_app` function:

```python
from aiohttp import web

from openapi.db import get_db

def setup_app(app: web.Application) -> None:
    db = get_db(app)
    meta = db.metadata

```

This will enable database connection and command line tools (most of them from [alembic][]):

```
python main.py db --help
```

The database container is available at the `db` app key:

```python
app['db']
```

## Environment Variables

Several environment variables are used by the library to support testing and deployment.

- `DATASTORE`: PostgreSql connection string (same as [SqlAlchemy][] syntax)
- `DBPOOL_MIN_SIZE`: minimum size of database connection pool (default is 10)
- `DBPOOL_MAX_SIZE`: maximum size of database connection pool (default is 10)

[aiohttp]: https://aiohttp.readthedocs.io/en/stable/
[openapi]: https://www.openapis.org/
[postgresql]: https://www.postgresql.org/
[sqlalchemy]: https://www.sqlalchemy.org/
[click]: https://github.com/pallets/click
[alembic]: http://alembic.zzzcomputing.com/en/latest/
[asyncpg]: https://github.com/MagicStack/asyncpg
