from aiohttp import web

from openapi import ws
from openapi.ws import pubsub


ws_routes = web.RouteTableDef()


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
