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


Backend
========

The websocket backend is implemented by subclassing the :class:`.SocketsManager` and implement the methods required by your application.
This example implements a very simple backend for testing the websocket module in unittests.


.. code-block:: python

    import asyncio

    from aiohttp import web
    from openapi.ws.manager import SocketsManager

    class LocalBroker(SocketsManager):
        """A local broker for testing"""

        def __init__(self):
            self.binds = set()
            self.messages: asyncio.Queue = asyncio.Queue()
            self.worker = None
            self._stop = False

        @classmethod
        def for_app(cls, app: web.Application) -> "LocalBroker":
            broker = cls()
            app.on_startup.append(broker.start)
            app.on_shutdown.append(broker.close)
            return broker

        async def start(self, *arg):
            if not self.worker:
                self.worker = asyncio.ensure_future(self._work())

        async def publish(self, channel: str, event: str, body: Any):
            """simulate network latency"""
            if channel.lower() != channel:
                raise CannotPublish
            payload = dict(event=event, data=self.get_data(body))
            asyncio.get_event_loop().call_later(
                0.01, self.messages.put_nowait, (channel, payload)
            )

        async def subscribe(self, channel: str) -> None:
            """ force channel names to be lowercase"""
            if channel.lower() != channel:
                raise CannotSubscribe

        async def close(self, *arg):
            self._stop = True
            await self.close_sockets()
            if self.worker:
                self.messages.put_nowait((None, None))
                await self.worker
                self.worker = None

        async def _work(self):
            while True:
                channel, body = await self.messages.get()
                if self._stop:
                    break
                await self.channels(channel, body)

        def get_data(self, data: Any) -> Any:
            if data == "error":
                return self.raise_error
            elif data == "runtime_error":
                return self.raise_runtime
            return data

        def raise_error(self):
            raise ValueError

        def raise_runtime(self):
            raise RuntimeError
