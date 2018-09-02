import asyncio

from aiohttp import web

from openapi import ws
from openapi.ws import pubsub


ws_routes = web.RouteTableDef()


class LocalPubSub(ws.Broker):

    def __init__(self):
        self.binds = set()
        self.messages = None
        self.worker = None
        self._stop = False

    async def publish(self, body, key):
        if not self.worker:
            self.messages = asyncio.Queue()
            self.worker = asyncio.ensure_future(self._work())
        asyncio.get_event_loop().call_later(
            0.01, self.messages.put_nowait, (body, key)
        )

    async def bind(self, key):
        self.binds.add(key)

    async def close(self):
        self._stop = True
        if self.worker:
            self.messages.put_nowait((None, None))
            await self.worker
            self.worker = None

    async def _work(self):
        while True:
            body, key = await self.messages.get()
            if self._stop:
                break
            if self.channels and key in self.binds:
                await self.channels(key, body)


@ws_routes.view('/stream')
class StreamPath(ws.WsPath, pubsub.Publish, pubsub.Subscribe):
    """
    ---
    summary: Create and query Tasks
    tags:
        - Task
    """
    async def ws_rpc_echo(self, payload):
        """Echo parameters
        """
        return payload
