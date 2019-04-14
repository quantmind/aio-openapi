from dataclasses import dataclass
from typing import Dict, List, Union

from ..data import fields
from .rpc import ws_rpc


@dataclass
class PublishSchema:
    data: Union[str, List, Dict]
    channel: str = fields.data_field(
        required=True, description="Channel to publish message"
    )
    event: str = fields.data_field(description="Channel event")


@dataclass
class SubscribeSchema:
    channel: str = fields.data_field(required=True, description="Channel to subscribe")
    event: str = fields.data_field(description="Channel event")


class Publish:
    """Implement the publish RPC call
    """

    def get_publish_message(self, data):
        return data

    @ws_rpc(body_schema=PublishSchema)
    async def ws_rpc_publish(self, payload):
        """Publish an event on a channel
        """
        event = payload.get("event")
        data = self.get_publish_message(payload.get("data"))
        return await self.channels.publish(payload["channel"], event, data)


class Subscribe:
    """Implement the subscribe and unsubscribe webcokst RPC
    """

    @ws_rpc(body_schema=SubscribeSchema)
    async def ws_rpc_subscribe(self, payload):
        """Subscribe to an event on a channel
        """
        await self.channels.register(
            payload["channel"], payload.get("event"), self.new_message
        )
        return dict(subscribed=self.channels.get_subscribed(self.new_message))

    @ws_rpc(body_schema=SubscribeSchema)
    async def ws_rpc_unsubscribe(self, payload):
        """Unsubscribe to an event on a channel
        """
        await self.channels.unregister(
            payload["channel"], payload.get("event"), self.new_message
        )
        return dict(subscribed=self.channels.get_subscribed(self.new_message))

    async def new_message(self, channel, match, data):
        """A new message has arrived from channels

        Send it to client
        """
        await self.write(dict(channel=channel.name, event=match, data=data))
