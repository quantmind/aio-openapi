# aio-openapi

[![PyPI version](https://badge.fury.io/py/aio-openapi.svg)](https://badge.fury.io/py/aio-openapi)
[![Python versions](https://img.shields.io/pypi/pyversions/aio-openapi.svg)](https://pypi.org/project/aio-openapi)

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

* Asynchronous web routes with [aiohttp](https://aiohttp.readthedocs.io/en/stable/)
* Data validation, serialization and unserialization with python [dataclasses](https://docs.python.org/3/library/dataclasses.html)
* [OpenApi](https://www.openapis.org/) v 3 auto documentation
* [SqlAlchemy](https://www.sqlalchemy.org/) expression language
* Asynchronous DB interaction with [asyncpg](https://github.com/MagicStack/asyncpg)
* Migrations with [alembic](http://alembic.zzzcomputing.com/en/latest/)
* SqlAlchemy tables as python dataclasses

## Websockets

This library provides a simple distributed websocket utility for creating
websocket remote procedure calls (RPC) and pub/sub.
```python
from aiohttp import web

from openapi.ws import Sockets

app = web.Application()
...
app['web_sockets'] = Sockets(app)
```
### RPC protocol

The RPC protocol has the following structure for incoming messages
```
{
    "id": "abc",
    "method": "rpc_method_name":
    "payload": {
        ...
    }
}
```
The ``id`` is used by clients to link the request with the corresponding response.
The response for an RPC call is eitrher a success
```
{
    "id": "abc",
    "method": "rpc_method_name":
    "result": {
        ...
    }
}
```
or error
```
{
    "id": "abc",
    "method": "rpc_method_name":
    "error": {
        ...
    }
}
```
### Publish/Subscribe

To subscribe to messages, one need to use the ``Subscribe`` mixin with the subscribe RPC handler.
Messages take the form:
```
{
    "channel": "channel_name",
    "event": "event_name":
    "data": {
        ...
    }
}
```
