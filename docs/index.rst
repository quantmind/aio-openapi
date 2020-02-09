.. aio-openapi

======================
Welcome to aio-openapi
======================

Asynchronous web middleware for aiohttp_ and serving Rest APIs with OpenAPI_ v 3
specification and with optional PostgreSql database bindings.

Current version is |release|.

Installation
============

.. code-block:: bash

    pip install aio-openapi

Clone the repository and create a virtual environment `venv`.

Install dependencies by running the install script

.. code-block:: bash

    ./dev/install.sh

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


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   reference



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
