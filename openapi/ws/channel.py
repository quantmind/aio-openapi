import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Sequence, Set

from .errors import ChannelCallbackError
from .utils import redis_to_py_pattern

CallbackType = Callable[[], None]

logger = logging.getLogger("trading.websocket")


@dataclass
class Event:
    name: str
    pattern: str
    regex: Any
    callbacks: Set[CallbackType] = field(default_factory=set)


@dataclass
class Channel:
    """A websocket channel"""

    name: str
    _events: Dict[str, Event] = field(default_factory=dict)

    @property
    def events(self):
        """List of event names this channel is registered with"""
        return tuple((e.name for e in self._events.values()))

    def __len__(self) -> int:
        return len(self._events)

    def __contains__(self, pattern: str) -> bool:
        return pattern in self._events

    def __iter__(self):
        return iter(self._events)

    def info(self) -> Dict:
        return {e.name: len(e.callbacks) for e in self._events.values()}

    async def __call__(self, message: Dict[str, Any]) -> Sequence[CallbackType]:
        """Execute callbacks from a new message

        Return callbacks which have raise WebsocketClosed or have raise an exception
        """
        event_name = message.get("event") or ""
        data = message.get("data")
        for event in tuple(self._events.values()):
            match = event.regex.match(event_name)
            if match:
                match = match.group()
                results = await asyncio.gather(
                    *[
                        self._execute_callback(callback, event, match, data)
                        for callback in event.callbacks
                    ]
                )
                return tuple(c for c in results if c)
        return ()

    def register(self, event_name: str, callback: CallbackType):
        """Register a ``callback`` for ``event_name``"""
        event_name = event_name or "*"
        pattern = self.event_pattern(event_name)
        event = self._events.get(pattern)
        if not event:
            event = Event(name=event_name, pattern=pattern, regex=re.compile(pattern))
            self._events[event.pattern] = event
        event.callbacks.add(callback)
        return event

    def get_subscribed(self, callback: CallbackType):
        events = []
        for event in self._events.values():
            if callback in event.callbacks:
                events.append(event.name)
        return events

    def unregister(self, event_name: str, callback: CallbackType):
        pattern = self.event_pattern(event_name)
        event = self._events.get(pattern)
        if event:
            return self.remove_event_callback(event, callback)

    def event_pattern(self, event):
        """Channel pattern for an event name"""
        return redis_to_py_pattern(event or "*")

    def remove_callback(self, callback: CallbackType) -> None:
        for key, event in tuple(self._events.items()):
            self.remove_event_callback(event, callback)

    def remove_event_callback(self, event: Event, callback: CallbackType) -> None:
        event.callbacks.discard(callback)
        if not event.callbacks:
            self._events.pop(event.pattern)

    async def _execute_callback(
        self, callback: CallbackType, event: Event, match: str, data: Any
    ):
        try:
            await callback(self.name, match, data)
        except ChannelCallbackError:
            return callback
        except Exception:
            logger.exception('callback exception: channel "%s" event "%s"', self, event)
            return callback
