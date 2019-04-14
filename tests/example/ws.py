import asyncio

from aiohttp import web

from openapi import ws
from openapi.spec.path import ApiPath
from openapi.ws import pubsub

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
        """Echo parameters
        """
        return payload

    async def ws_rpc_cancel(self, payload):
        """Echo parameters
        """
        raise asyncio.CancelledError

    async def ws_rpc_badjson(self, payload):
        """Echo parameters
        """
        return ApiPath
