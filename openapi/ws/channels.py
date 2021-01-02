from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple

from openapi.data.validate import ValidationErrors

from .channel import CallbackType, Channel
from .errors import CannotSubscribe

if TYPE_CHECKING:
    from .manager import SocketsManager


class Channels:
    """Manage channels for publish/subscribe"""

    def __init__(self, sockets: "SocketsManager") -> None:
        self.sockets: "SocketsManager" = sockets
        self.channels: Dict[str, Channel] = {}

    @property
    def registered(self) -> Tuple[str, ...]:
        """Registered channels"""
        return tuple(self.channels)

    def __len__(self) -> int:
        return len(self.channels)

    def __contains__(self, channel_name: str) -> bool:
        return channel_name in self.channels

    def __iter__(self) -> Iterator[Channel]:
        return iter(self.channels.values())

    def clear(self) -> None:
        self.channels.clear()

    def info(self) -> Dict:
        return {channel.name: channel.info() for channel in self}

    async def __call__(self, channel_name: str, message: Dict) -> None:
        """Channel callback"""
        channel = self.channels.get(channel_name)
        if channel:
            closed = await channel(message)
            for websocket in closed:
                for channel_name, channel in tuple(self.channels.items()):
                    channel.remove_callback(websocket)
                    await self._maybe_remove_channel(channel)

    async def register(
        self, channel_name: str, event: str, callback: CallbackType
    ) -> Channel:
        """Register a callback

        :param channel_name: name of the channel
        :param event: name of the event in the channel
        :param callback: the callback to invoke when the `event` on `channel` occurs
        """
        channel_name = channel_name.lower()
        channel = self.channels.get(channel_name)
        if channel is None:
            try:
                await self.sockets.subscribe(channel_name)
            except CannotSubscribe:
                raise ValidationErrors(dict(channel="Invalid channel"))
            else:
                channel = Channel(channel_name)
                self.channels[channel_name] = channel
        channel.register(event, callback)
        return channel

    async def unregister(
        self, channel_name: str, event: str, callback: CallbackType
    ) -> Optional[Channel]:
        """Safely unregister a callback from the list of event
        callbacks for channel_name
        """
        channel = self.channels.get(channel_name.lower())
        if channel is None:
            raise ValidationErrors(dict(channel="Invalid channel"))
        channel.unregister(event, callback)
        return await self._maybe_remove_channel(channel)

    async def _maybe_remove_channel(self, channel: Channel) -> Channel:
        if not channel:
            await self.sockets.unsubscribe(channel.name)
            self.channels.pop(channel.name)
        return channel

    def get_subscribed(self, callback: CallbackType) -> Dict[str, List[str]]:
        subscribed = {}
        for channel in self.channels.values():
            events = channel.get_subscribed(callback)
            if events:
                subscribed[channel.name] = events
        return subscribed
