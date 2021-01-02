import asyncio
from typing import Any, Callable, Dict, Set

from ..utils import cached_property
from .channels import CannotSubscribe, Channels
from .errors import CannotPublish

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

    @cached_property
    def channels(self) -> Channels:
        """Set of connected :class:`.Websocket`"""
        return Channels(self)

    def add(self, ws: Websocket) -> None:
        """Add a new websocket to the connected set"""
        self.sockets.add(ws)

    def remove(self, ws: Websocket) -> None:
        """Remove a websocket from the connected set"""
        self.sockets.discard(ws)

    def server_info(self) -> Dict:
        return dict(connections=len(self.sockets), channels=self.channels.info())

    async def close_sockets(self) -> None:
        """Close and remove all websockets from the connected set"""
        await asyncio.gather(*[view.response.close() for view in self.sockets])
        self.sockets.clear()
        self.channels.clear()

    async def publish(
        self, channel: str, event: str, body: Dict
    ) -> None:  # pragma: no cover
        """Publish an event to a channel

        This method should raise :class:`.CannotPublish` if not possible to publish
        """
        raise CannotPublish

    async def subscribe(self, channel: str) -> None:  # pragma: no cover
        """Subscribe to a channel"""
        raise CannotSubscribe

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel"""
