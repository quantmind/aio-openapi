.. _aio-openapi-reference:

=========
Reference
=========


Data
====

DataView
--------

.. module:: openapi.data.view

.. autoclass:: DataView
   :members:

TypeInfo
--------

.. module:: openapi.utils

.. autoclass:: TypingInfo
   :members:


.. _aio-openapi-data-fields:

Data Fields
===========

.. module:: openapi.data.fields

.. autofunction:: data_field


String field
------------
.. autofunction:: str_field

Bool field
----------
.. autofunction:: bool_field

UUID field
-------------
.. autofunction:: uuid_field


Numeric field
-------------
.. autofunction:: number_field


Integer field
-------------
.. autofunction:: integer_field


Email field
-------------
.. autofunction:: email_field

Enum field
----------

.. autofunction:: enum_field

Date field
----------

.. autofunction:: date_field

Datetime field
--------------

.. autofunction:: date_time_field


JSON field
----------

.. autofunction:: json_field

Data Validation
===============

.. module:: openapi.data.validate

Validate
-----------------------

The entry function to validate input data and return a python representation.
The function accept as input a valid type annotation or a :class:`.TypingInfo` object.

.. autofunction:: validate


Validate Schema
-----------------------

Same as the :func:`.validate` but returns the validation schema object rather than
simple data types (this is mainly different for dataclasses)

.. autofunction:: validated_schema


Dataclass from db table
-----------------------
.. module:: openapi.data.db

.. autofunction:: dataclass_from_table


Dump data
---------
.. module:: openapi.data.dump

.. autofunction:: dump


Openapi Specification
======================

.. module:: openapi.spec

OpenApiInfo
-------------

.. autoclass:: OpenApiInfo
   :members:


OpenApiSpec
-------------

.. autoclass:: OpenApiSpec
   :members:


op decorator
------------

Decorator for specifying schemas at route/method level. It is used by both
the business logic as well the auto-documentation.

.. autoclass:: op

Redoc
------------

Allow to add redoc_ redering to your api.

.. autoclass:: Redoc

DB
==

This module provides integration with SqlAlchemy_ asynchronous engine for postgresql.
The connection string supported is of this type only::

   postgresql+asyncpg://<db_user>:<db_password>@<db_host>:<db_port>/<db_name>


.. module:: openapi.db.container


Database
--------

.. autoclass:: Database
   :members:
   :member-order: bysource
   :special-members: __getattr__


.. module:: openapi.db.dbmodel

CrudDB
------

Database container with CRUD operations. Used extensively by the :class:`.SqlApiPath` routing class.


.. autoclass:: CrudDB
   :members:


get_db
-------

.. module:: openapi.db

.. autofunction:: get_db


.. module:: openapi.testing

SingleConnDatabase
------------------

A :class:`.CrudDB` container for testing database driven Rest APIs.

.. autoclass:: SingleConnDatabase
   :members:


Routes
======


ApiPath
----------

.. module:: openapi.spec.path

.. autoclass:: ApiPath
   :members:
   :member-order: bysource


SqlApiPath
----------

.. module:: openapi.db.path

.. autoclass:: SqlApiPath
   :members:
   :member-order: bysource


Websocket
=========

.. module:: openapi.ws.manager


Websocket RPC
-------------

.. autoclass:: Websocket
   :members:
   :member-order: bysource


SocketsManager
--------------

.. autoclass:: SocketsManager
   :members:
   :member-order: bysource


Channels
-----------

.. module:: openapi.ws.channels

.. autoclass:: Channels
   :members:
   :member-order: bysource


Channel
-----------

.. module:: openapi.ws.channel

.. autoclass:: Channel
   :members:
   :member-order: bysource


WsPathMixin
-----------

.. module:: openapi.ws.path


.. autoclass:: WsPathMixin
   :members:
   :member-order: bysource


.. module:: openapi.ws.pubsub

Subscribe
-----------

.. autoclass:: Subscribe
   :members:
   :member-order: bysource

Publish
-----------

.. autoclass:: Publish
   :members:
   :member-order: bysource


.. _redoc: https://gith
.. _SqlAlchemy: https://www.sqlalchemy.org/
