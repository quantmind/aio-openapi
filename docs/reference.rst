
=========
Reference
=========


Data
====

.. module:: openapi.data.view

.. autoclass:: DataView
   :members:

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


Spec
====

.. module:: openapi.spec

.. autoclass:: op

.. autoclass:: ApiPath
   :members:


DB
==

.. module:: openapi.db.container

.. autoclass:: Database
   :members:
   :member-order: bysource
   :special-members: __getattr__

.. module:: openapi.db.dbmodel

.. autoclass:: CrudDB
   :members:

.. module:: openapi.db.path

.. autoclass:: SqlApiPath
   :members:

Websocket
=========
