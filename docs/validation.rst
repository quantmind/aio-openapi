.. _aio-openapi-validation:


===========
 Validation
===========

Validation is an important component of the library and it is designed to validate
data to and from JSON serializable objects.

To validate a simple list of integers

.. code-block:: python

    from typing import List

    from openapi.data.validate import validate

    validate(List[int], [5,2,4,8])
    # ValidatedData(data=[5, 2, 4, 8], errors={})

    validate(List[int], [5,2,"5",8])
    # ValidatedData(data=None, errors='not valid type')

The main object for validation are python dataclasses:


.. code-block:: python

    from dataclasses import dataclass
    from typing import Union

    @dataclass
    class Foo:
        text: str
        param: Union[str, int]
        done: bool = False


    validate(Foo, {})
    # ValidatedData(data=None, errors={'text': 'required', 'param': 'required'})

    validate(Foo, dict(text=1))
    # ValidatedData(data=None, errors={'text': 'not valid type', 'param': 'required'})

    validate(Foo, dict(text="ciao", param=3))
    # ValidatedData(data={'text': 'ciao', 'param': 3, 'done': False}, errors={})


.. _aio-openapi-schema:

Supported Schema
================

The library support the following schemas

* Primitive types: ``str``, ``int``, ``float``, ``bool``, ``date``, ``datetime`` and ``Decimal``
* Python :mod:`dataclasses` with fields from this supported schema
* ``List`` from ``typing`` annotation with items from this supported schema
* ``Dict`` from ``typing`` with keys as string and items from this supported schema
* ``Union`` from ``typing`` with items from this supported schema

Validated Schema
================

Use the :func:`.validated_schema` to validate input data and return an instance of the
validation schema. This differs from :func:`.validate` only when dataclasses are involved

.. code-block:: python

    from openapi.data.validate import validated_schema

    validated_schema(Foo, dict(text="ciao", param=3))
    # Foo(text='ciao', param=3, done=False)


Dump
====

Validated schema can be dump into valid JSON via the :func:`.dump` function
