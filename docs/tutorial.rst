.. _aio-openapi-tutorial:

========
Tutorial
========

Lets create a simple application


.. code-block:: python

    from aiohttp import web
    from openapi.rest import rest


    def create_app():
        return rest(setup_app=setup_app)


    def setup_app(app: web.Application) -> None:
        ...



if the ``openapi`` entry is not specified the server won't add any of the tooling related to openapi
auto-documenation, which means no spec path as specified by the **SPEC_ROUTE** :ref:`env variable <aio-openapi-env>`.
