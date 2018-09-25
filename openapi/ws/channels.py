import asyncio
from collections import OrderedDict
from typing import Union, Dict, Iterator, Callable

from .channel import Channel, StatusType, logger
from .utils import redis_to_py_pattern
from .broker import Broker
from ..utils import compact


DEFAULT_CHANNEL = 'server'

CAN_CONNECT = frozenset((StatusType.initialised, StatusType.disconnected))
MIN_RECONNECT_LAG = 2
MAX_RECONNECT_LAG = 20


def backoff(value):
    return min(value*1.2, MAX_RECONNECT_LAG) if value else MIN_RECONNECT_LAG


class Channels:
    """Manage channels for publish/subscribe
    """
    statusType = StatusType

    def __init__(
            self,
            broker: Broker,
            namespace: str=None,
            status_channel: str=None) -> None:
        self.connection_error = False
        self.broker = broker
        self.namespace = (namespace or '').lower()
        self.channels = OrderedDict()
        self.status_channel = self.get_channel(
            status_channel or DEFAULT_CHANNEL)
        self.status = self.statusType.initialised
        if broker:
            broker.set_channels(self)

    @property
    def registered(self):
        return tuple(self.channels)

    def __repr__(self) -> str:
        return f'Channels [{self.broker}]'

    def __str__(self) -> str:
        return self.__repr__()

    def __len__(self) -> int:
        return len(self.channels)

    def __contains__(self, name) -> bool:
        return name in self.channels

    def __iter__(self) -> Iterator:
        return iter(self.channels.values())

    async def __call__(self, channel_name: str, message: Union[str, Dict]):
        if channel_name.startswith(self.namespace):
            name = channel_name[len(self.namespace):]
            channel = self.channels.get(name)
            if channel:
                await channel(message)

    async def register(
            self,
            channel_name: str,
            event: str,
            callback: Callable) -> Channel:
        """Register a callback to ``channel_name`` and ``event``
        """
        channel = self.get_channel(channel_name)
        channel.register(event, callback)
        await self.connect()
        await channel.connect()
        return channel

    async def unregister(
            self,
            channel_name: str,
            event: str,
            callback: Callable) -> Channel:
        """Safely unregister a callback from the list of event
        callbacks for channel_name
        """
        channel = self.get_channel(channel_name, create=False)
        if channel:
            channel.unregister(event, callback)
            if not channel:
                await channel.disconnect()
                self.channels.pop(channel.name)
        return channel

    async def connect(self, next_time=None):
        """Connect with broker if possible
        """
        if self.status in CAN_CONNECT:
            self.status = self.statusType.connecting
            await self._connect(next_time)

    async def publish(self, channel_name, event=None, data=None):
        """Publish a new ``event`` on a ``channel_name``
        """
        await self.connect()
        msg = compact(event=event, channel=channel_name, data=data)
        try:
            await self.broker.publish(self.prefixed(channel_name), msg)
        except ConnectionRefusedError:
            self.connection_error = True
            logger.critical(
                '%s cannot publish on "%s" channel - connection error',
                self,
                channel_name
            )
        else:
            self._connection_ok()
        return msg

    def prefixed(self, name):
        if self.namespace and not name.startswith(self.namespace):
            name = f'{self.namespace}{name}'
        return name

    async def start(self):
        if self.broker:
            await self.broker.start()

    async def close(self):
        """Close channels and underlying broker handler
        """
        self.status = self.statusType.closed
        if self.broker:
            await self.broker.close()

    def get_channel(self, name, create=True):
        name = name.lower()
        channel = self.channels.get(name)
        if channel is None and create:
            channel = Channel(self, name)
            self.channels[channel.name] = channel
        return channel

    def event_pattern(self, event):
        """Channel pattern for an event name
        """
        return redis_to_py_pattern(event or '*')

    # INTERNALS

    async def _subscribe(self, channel_name):
        """Subscribe to the remote server
        """
        await self.broker.subscribe(self.prefixed(channel_name))

    async def _unsubscribe(self, channel_name):
        pass

    def _connection_ok(self):
        if self.connection_error:
            logger.warning(
                'connection with %s established - all good',
                self
            )
            self.connection_error = False

    async def _connect(self, next_time):
        try:
            # register
            self.status = self.statusType.connecting
            await self._subscribe(self.status_channel.name)
            self.status = StatusType.connected
            logger.warning(
                '%s ready and listening for events on channel "%s" - all good',
                self,
                self.status_channel.name
            )
        except ConnectionError:
            self.status = StatusType.disconnected
            next_time = backoff(next_time)
            logger.critical(
                '%s cannot subscribe - connection error - '
                'try again in %s seconds',
                self,
                next_time
            )
            self._loop.call_later(
                next_time,
                lambda: self._loop.create_task(self.connect(next_time))
            )
        else:
            await asyncio.gather(*[
                c.connect() for c in self if c.name != self.status_channel.name
            ])
