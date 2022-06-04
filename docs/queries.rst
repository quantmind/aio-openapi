.. _aio-openapi-queries:


========
 Queries
========

.. module:: openapi.pagination

The library provide some useful tooling for creating dataclasses for validating schema when querying paginated endpoints.

Pagination
===========

Base class
------------

.. autoclass:: Pagination
   :members:


Paginated Data
---------------

.. autoclass:: PaginatedData
   :members:


Visitor
------------
.. autoclass:: PaginationVisitor
   :members:


Limit/Offset Pagination
=========================

.. autofunction:: offsetPagination


Cursor Pagination
=========================

.. autofunction:: cursorPagination



searchable
==========

.. autofunction:: searchable
