from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Dict, List, Union

from ..data import fields
from ..data.validate import ValidationErrors
from .channel import logger
from .errors import CONNECTION_ERRORS, CannotPublish, ChannelCallbackError
from .rpc import ws_rpc

if TYPE_CHECKING:  # pragma: no cover
    from .path import WsPathMixin


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


class ChannelCallback:
    """Callback for channels"""

    def __init__(self, ws: "WsPathMixin"):
        self.ws: "WsPathMixin" = ws

    def __repr__(self) -> str:  # pragma: no cover
        return self.ws.socket_id

    def __str__(self) -> str:
        return f"websocket {self.ws.socket_id}"

    async def __call__(self, channel: str, match: str, data: Any) -> None:
        try:
            if hasattr(data, "__call__"):
                data = data()
            await self.ws.write(dict(channel=channel, event=match, data=data))
        except CONNECTION_ERRORS:
            logger.info("lost connection with %s", self)
            await self.ws.close()
            raise ChannelCallbackError
        except Exception:
            logger.exception("Critical exception on connection %s", self)
            await self.ws.close()
            raise ChannelCallbackError


class Publish:
    """Mixin which implements the publish RPC method

    Must be used as mixin of :class:`.WsPathMixin`
    """

    def get_publish_message(self, data: Any) -> Any:
        """Create the publish message from the data payload"""
        return data

    @ws_rpc(body_schema=PublishSchema)
    async def ws_rpc_publish(self, payload):
        """Publish an event on a channel"""
        try:
            event = payload.get("event")
            data = self.get_publish_message(payload.get("data"))
            await self.sockets.publish(payload["channel"], event, data)
            return dict(channel=payload["channel"], event=event, data=data)
        except CannotPublish:
            raise ValidationErrors(dict(channel="Cannot publish to channel"))


class Subscribe:
    """Mixin which implements the subscribe and unsubscribe RPC methods

    Must be used as mixin of :class:`.WsPathMixin`
    """

    @cached_property
    def channel_callback(self) -> ChannelCallback:
        """The callback for :class:`.Channels`"""
        return ChannelCallback(self)

    @ws_rpc(body_schema=SubscribeSchema)
    async def ws_rpc_subscribe(self, payload):
        """Subscribe to an event on a channel"""
        await self.channels.register(
            payload["channel"], payload.get("event"), self.channel_callback
        )
        return dict(subscribed=self.channels.get_subscribed(self.channel_callback))

    @ws_rpc(body_schema=SubscribeSchema)
    async def ws_rpc_unsubscribe(self, payload):
        """Unsubscribe to an event on a channel"""
        await self.channels.unregister(
            payload["channel"], payload.get("event"), self.channel_callback
        )
        return dict(subscribed=self.channels.get_subscribed(self.channel_callback))
