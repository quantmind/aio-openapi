import asyncio
from typing import Any

from aiohttp import web

from openapi import ws
from openapi.spec.path import ApiPath
from openapi.ws import CannotPublish, CannotSubscribe, pubsub
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

    async def ws_rpc_server_info(self, payload):
        """Websocket server information"""
        return self.sockets.server_info()

    async def ws_rpc_cancel(self, payload):
        """Echo parameters"""
        raise asyncio.CancelledError

    async def ws_rpc_badjson(self, payload):
        """Echo parameters"""
        return ApiPath


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
