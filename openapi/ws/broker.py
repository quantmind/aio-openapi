import abc
import asyncio
from typing import Dict


class Broker(abc.ABC):
    """Abstract class for pubsub
    """
    channels = None

    def set_channels(self, channels) -> None:
        self.channels = channels

    async def start(self) -> None:
        """
        Start broker
        """

    async def close(self):
        """
        Close broker
        """

    @abc.abstractmethod
    async def publish(self, body: Dict, routing_key: str):
        """Publish a new payload to a routing key
        """
        pass

    @abc.abstractmethod
    async def bind(self, routing_key: str):
        """Bind the broker to a routing key"""
        pass


class LocalBroker(Broker):

    def __init__(self):
        self.binds = set()
        self.messages = None
        self.worker = None
        self._stop = False

    async def start(self):
        if not self.worker:
            self.messages = asyncio.Queue()
            self.worker = asyncio.ensure_future(self._work())

    async def publish(self, body, channel, event):
        asyncio.get_event_loop().call_later(
            0.01, self.messages.put_nowait, (body, channel, event)
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
