.. _aio-openapi-websocket:


==============
 Websocket RPC
==============


The library includes a minimal API for Websocket JSON-RPC (remote procedure calls).

To add websockets RPC you need to create a websocket route:

.. code-block:: python

    from aiohttp import web
    from openapi.spec import ApiPath
    from openapi.ws import WsPathMixin
    from openapi.ws.pubsub import Publish, Subscribe

    ws_routes = web.RouteTableDef()

    @ws_routes.view("/stream")
    class Websocket(ApiPath, WsPathMixin, Subscribe, Publish):

        async def ws_rpc_info(self, payload):
            """Server information"""
            return self.sockets.server_info()

the :class:`.WsPathMixin` adds the get method for accepting websocket requests with the RPC protocol.
:class:`.Subscribe` and :class:`.Publish` are optional mixins for adding
Pub/Sub RPC methods to the endpoint.

The endpoint can be added to an application in the setup function:

.. code-block:: python

    from aiohttp.web import Application

    from openapi.ws import SocketsManager

    def setup_app(app: Application) -> None:
        app['web_sockets'] = SocketsManager()
        app.router.add_routes(ws_routes)

RPC protocol
===============

The RPC protocol has the following structure for incoming messages

.. code-block:: javascript

    {
        "id": "abc",
        "method": "rpc_method_name",
        "payload": {
            ...
        }
    }

The `id` is used by clients to link the request with the corresponding response.
The response for an RPC call is either a success

.. code-block:: javascript

    {
        "id": "abc",
        "method": "rpc_method_name",
        "response": {
            ...
        }
    }


or an error

.. code-block:: javascript

    {
        "id": "abc",
        "method": "rpc_method_name":
        "error": {
            ...
        }
    }


Publish/Subscribe
=================

To subscribe to messages, one need to use the :class:`.Subscribe` mixin with the websocket route (like we have done in this example).
Messages take the form:

.. code-block:: javascript

    {
        "channel": "channel_name",
        "event": "event_name",
        "data": {
            ...
        }
    }
