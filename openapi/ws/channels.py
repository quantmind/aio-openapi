from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple

from openapi.data.validate import ValidationErrors

from .channel import CallbackType, Channel
from .errors import CannotSubscribe

if TYPE_CHECKING:  # pragma: no cover
    from .manager import SocketsManager


class Channels:
    """Manage channels for publish/subscribe"""

    def __init__(self, sockets: "SocketsManager") -> None:
        self.sockets: "SocketsManager" = sockets
        self._channels: Dict[str, Channel] = {}

    @property
    def registered(self) -> Tuple[str, ...]:
        """Registered channels"""
        return tuple(self._channels)

    def __len__(self) -> int:
        return len(self._channels)

    def __contains__(self, channel_name: str) -> bool:
        return channel_name in self._channels

    def __iter__(self) -> Iterator[Channel]:
        return iter(self._channels.values())

    def clear(self) -> None:
        self._channels.clear()

    def get(self, channel_name: str) -> Optional[Channel]:
        return self._channels.get(channel_name)

    def info(self) -> Dict:
        return {channel.name: channel.info() for channel in self}

    async def __call__(self, channel_name: str, message: Dict) -> None:
        """Channel callback"""
        channel = self.get(channel_name)
        if channel:
            closed = await channel(message)
            for websocket in closed:
                for channel_name, channel in tuple(self._channels.items()):
                    channel.remove_callback(websocket)
                    await self._maybe_remove_channel(channel)

    async def register(
        self, channel_name: str, event_name: str, callback: CallbackType
    ) -> Channel:
        """Register a callback

        :param channel_name: name of the channel
        :param event_name: name of the event in the channel or a pattern
        :param callback: the callback to invoke when the `event` on `channel` occurs
        """
        channel = self.get(channel_name)
        if channel is None:
            try:
                await self.sockets.subscribe(channel_name)
            except CannotSubscribe:
                raise ValidationErrors(dict(channel="Invalid channel"))
            else:
                channel = Channel(channel_name)
                self._channels[channel_name] = channel
        event = channel.register(event_name, callback)
        await self.sockets.subscribe_to_event(channel.name, event.name)
        return channel

    async def unregister(
        self, channel_name: str, event: str, callback: CallbackType
    ) -> Optional[Channel]:
        """Safely unregister a callback from the list of event
        callbacks for channel_name
        """
        channel = self.get(channel_name)
        if channel is None:
            raise ValidationErrors(dict(channel="Invalid channel"))
        channel.unregister(event, callback)
        return await self._maybe_remove_channel(channel)

    async def _maybe_remove_channel(self, channel: Channel) -> Channel:
        if not channel:
            await self.sockets.unsubscribe(channel.name)
            self._channels.pop(channel.name)
        return channel

    def get_subscribed(self, callback: CallbackType) -> Dict[str, List[str]]:
        subscribed = {}
        for channel in self:
            events = channel.get_subscribed(callback)
            if events:
                subscribed[channel.name] = events
        return subscribed
