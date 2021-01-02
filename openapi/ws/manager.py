import asyncio
from functools import cached_property
from typing import Any, Callable, Dict, Set

WsHandlerType = Callable[[str, Any], None]


class Websocket:
    """A websocket connection"""

    socket_id: str = ""
    """websocket ID"""

    def __str__(self) -> str:
        return self.socket_id


class SocketsManager:
    """A base class for websocket managers"""

    @cached_property
    def sockets(self) -> Set[Websocket]:
        """Set of connected :class:`.Websocket`"""
        return set()

    def add(self, ws: Websocket) -> None:
        """Add a new websocket to the connected set"""
        self.sockets.add(ws)

    def remove(self, ws: Websocket) -> None:
        """Remove a websocket from the connected set"""
        self.sockets.discard(ws)

    def server_info(self) -> Dict:
        return dict(
            connections=len(self.sockets),
        )

    async def close_sockets(self):
        """Close and remove all websockets from the connected set"""
        await asyncio.gather(*[view.response.close() for view in self.sockets])
        self.sockets.clear()

    async def publish(self, channel: str, body: Dict) -> None:
        """Publish a new payload to a channel/exchange"""

    async def subscribe(self, channel: str, handler: WsHandlerType) -> None:
        """Bind the broker to a channel/exchange"""

    async def unsubscribe(self, channel: str) -> None:
        """Bind the broker to a channel/exchange"""

    def on_connection_lost(self, lost):
        pass
