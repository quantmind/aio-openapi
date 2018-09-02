# aio-openapi

[![PyPI version](https://badge.fury.io/py/aio-openapi.svg)](https://badge.fury.io/py/aio-openapi)

[![CircleCI](https://circleci.com/gh/lendingblock/aio-openapi.svg?style=svg)](https://circleci.com/gh/lendingblock/aio-openapi)

[![codecov](https://codecov.io/gh/lendingblock/aio-openapi/branch/master/graph/badge.svg)](https://codecov.io/gh/lendingblock/aio-openapi)

Asynchronous web middleware for Rest APIs with PostgreSql Database.

## Installation
```
pip install aio-openapi
```

## Development

Clone the repository and create a virtual environment `venv`.

Install dependencies by running the install script
```
./dev/install.sh
```
To run tests
```
pytest --cov
```

## Features

* Asynchronous web routes with [aiohttp][]
* Data validation, serialization and unserialization with python [dataclasses][]
* [OpenApi](https://www.openapis.org/) v 3 auto documentation
* [SqlAlchemy](https://www.sqlalchemy.org/) expression language
* Asynchronous DB interaction with [asyncpg][]
* Migrations with [alembic][]
* SqlAlchemy tables as python [dataclasses][]

## Websockets

This library provides a simple distributed websocket utility for creating
websocket remote procedure calls (RPC) and pub/sub.
```python
from aiohttp import web

from openapi.ws import Sockets

app = web.Application()
...
app['web_sockets] = Sockets(app)
```

[aiohttp]: https://aiohttp.readthedocs.io/en/stable/
[asyncpg]: https://github.com/MagicStack/asyncpg
[dataclasses]: https://docs.python.org/3/library/dataclasses.html
[alembic]: http://alembic.zzzcomputing.com/en/latest/
