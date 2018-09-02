import abc
from typing import Dict


class Broker(abc.ABC):
    """Abstract class for pubsub
    """
    channels = None

    def set_channels(self, channels) -> None:
        self.channels = channels

    @abc.abstractmethod
    async def publish(self, body: Dict, routing_key: str):
        """Publish a new payload to a routing key
        """
        pass

    @abc.abstractmethod
    async def bind(self, routing_key: str):
        """Bind the broker to a routing key"""
        pass
