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


Openapi Spec
==================

.. module:: openapi.spec

OpenApiSpec
-------------

.. autoclass:: OpenApiSpec


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


.. _redoc: https://github.com/Redocly/redoc
