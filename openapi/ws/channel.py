import asyncio
import enum
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass
from functools import wraps
from typing import Set

logger = logging.getLogger("openapi.channels")


class StatusType(enum.Enum):
    initialised = 1
    connecting = 2
    connected = 3
    disconnected = 4
    closed = 5


class CallbackError(Exception):
    """Exception which allow for a clean callback removal
    """


@dataclass
class Event:
    name: str
    pattern: str
    regex: object
    callbacks: Set


def safe_execution(method):
    @wraps(method)
    async def _(self, *args, **kwargs):
        try:
            await method(self, *args, **kwargs)
        except ConnectionError:
            self.channels.status = StatusType.disconnected
            await self.channels.connect()

    return _


class Channel:
    """A websocket channel
    """

    def __init__(self, channels, name):
        self.channels = channels
        self.name = name
        self.callbacks = OrderedDict()

    @property
    def events(self):
        """List of event names this channel is registered with
        """
        return tuple((e.name for e in self.callbacks.values()))

    def __repr__(self):
        return repr(self.callbacks)

    def __len__(self):
        return len(self.callbacks)

    def __contains__(self, pattern):
        return pattern in self.callbacks

    def __iter__(self):
        return iter(self.channels.values())

    async def __call__(self, message):
        event = message.get("event") or ""
        data = message.get("data")
        for entry in tuple(self.callbacks.values()):
            match = entry.regex.match(event)
            if match:
                match = match.group()
                coros = [
                    self.execute_callback(cb, entry, event, match, data)
                    for cb in entry.callbacks
                ]
                await asyncio.gather(*coros)

    async def execute_callback(self, callback, entry, event, match, data):
        try:
            await callback(self, match, data)
        except CallbackError:
            self._remove_callback(entry, callback)
        except Exception:
            self._remove_callback(entry, callback)
            logger.exception(
                'callback exception: channel "%s" event "%s"', self.name, event
            )

    @safe_execution
    async def connect(self):
        channels = self.channels
        if channels.status == StatusType.connected:
            await self.channels._subscribe(self.name)

    @safe_execution
    async def disconnect(self):
        channels = self.channels
        if channels.status == StatusType.connected:
            await self.channels._unsubscribe(self.name)

    def register(self, event, callback):
        """Register a ``callback`` for ``event``
        """
        event = event or "*"
        pattern = self.channels.event_pattern(event)
        entry = self.callbacks.get(pattern)
        if not entry:
            entry = Event(
                name=event, pattern=pattern, regex=re.compile(pattern), callbacks=[]
            )
            self.callbacks[entry.pattern] = entry

        if callback not in entry.callbacks:
            entry.callbacks.append(callback)

        return entry

    def get_subscribed(self, handler):
        events = []
        for event in self.callbacks.values():
            if handler in event.callbacks:
                events.append(event.name)
        return events

    def unregister(self, event, callback):
        pattern = self.channels.event_pattern(event)
        entry = self.callbacks.get(pattern)
        if entry:
            return self._remove_callback(entry, callback)

    def _remove_callback(self, entry, callback):
        if callback in entry.callbacks:
            entry.callbacks.remove(callback)
            if not entry.callbacks:
                self.callbacks.pop(entry.pattern)
            return entry
