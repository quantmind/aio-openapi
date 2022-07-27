.. aio-openapi

======================
Welcome to aio-openapi
======================

Asynchronous web middleware for aiohttp_ and serving Rest APIs with OpenAPI_ v 3
specification and with optional PostgreSql database bindings.

Current version is |release|.

Installation
============

It requires python 3.8 or above.

.. code-block:: bash

    pip install aio-openapi

Development
===========

Clone the repository and install dependencies (via poetry):

.. code-block:: bash

    make install

To run tests

.. code-block:: bash

    poetry run pytest --cov


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
