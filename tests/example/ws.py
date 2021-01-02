import asyncio

from aiohttp import web

from openapi import ws
from openapi.spec.path import ApiPath
from openapi.ws import Channels, WsHandlerType, pubsub
from openapi.ws.manager import SocketsManager

ws_routes = web.RouteTableDef()


@ws_routes.view("/stream")
class StreamPath(ws.WsPathMixin, pubsub.Publish, pubsub.Subscribe, ApiPath):
    """
    ---
    summary: Create and query Tasks
    tags:
        - Task
    """

    async def ws_rpc_echo(self, payload):
        """Echo parameters"""
        return payload

    async def ws_rpc_cancel(self, payload):
        """Echo parameters"""
        raise asyncio.CancelledError

    async def ws_rpc_badjson(self, payload):
        """Echo parameters"""
        return ApiPath


class LocalBroker(SocketsManager):
    """A local broker, mainly for testing"""

    def __init__(self, **kwargs):
        self.binds = set()
        self.channels = Channels(self, **kwargs)
        self.messages: asyncio.Queue = asyncio.Queue()
        self.worker = None
        self._stop = False
        self._handlers = set()

    @classmethod
    def for_app(cls, app: web.Application, **kwargs) -> "LocalBroker":
        broker = cls(**kwargs)
        app.on_startup.append(broker.start)
        app.on_shutdown.append(broker.close)
        return broker

    async def start(self, *arg):
        if not self.worker:
            self.worker = asyncio.ensure_future(self._work())

    async def publish(self, channel, body):
        asyncio.get_event_loop().call_later(
            0.01, self.messages.put_nowait, (channel, body)
        )

    async def subscribe(self, key: str, handler: WsHandlerType) -> None:
        self.binds.add(key)
        self._handlers.add(handler)

    async def unsubscribe(self, key):
        self.binds.discard(key)

    async def close(self, *arg):
        self._stop = True
        await self.close_sockets()
        if self.worker:
            self.messages.put_nowait((None, None))
            await self.worker
            self.worker = None

    async def _work(self):
        while True:
            key, body = await self.messages.get()
            if self._stop:
                break
            if key in self.binds:
                for handler in self._handlers:
                    await handler(key, body)
