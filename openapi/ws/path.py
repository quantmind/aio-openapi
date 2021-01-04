import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict

from aiohttp import web

from openapi.ws.channels import Channels

from .. import json
from ..data.validate import ValidationErrors, validated_schema
from ..utils import compact
from .errors import CONNECTION_ERRORS
from .manager import SocketsManager, Websocket

logger = logging.getLogger("openapi.ws")


@dataclass
class RpcProtocol:
    id: str
    method: str
    payload: Dict = field(default_factory=dict)


class ProtocolError(RuntimeError):
    pass


class WsPathMixin(Websocket):
    """Api Path mixin for Websocket RPC protocol"""

    SOCKETS_KEY = "web_sockets"
    """Key in the app where the Web Sockets manager is located"""

    @property
    def sockets(self) -> SocketsManager:
        """Connected websockets"""
        return self.request.app[self.SOCKETS_KEY]

    @property
    def channels(self) -> Channels:
        """Channels for pub/sub"""
        return self.sockets.channels

    async def get(self):
        response = web.WebSocketResponse()
        available = response.can_prepare(self.request)
        if not available:
            raise web.HTTPBadRequest(
                **self.api_response_data(
                    {"message": "Unable to open websocket connection"}
                )
            )
        await response.prepare(self.request)
        self.response = response
        self.started = time.time()
        key = "%s - %s" % (self.request.remote, self.started)
        self.socket_id = hashlib.sha224(key.encode("utf-8")).hexdigest()
        #
        # Add to set of sockets if available
        self.sockets.add(self)
        #
        try:
            async for msg in response:
                if msg.type == web.WSMsgType.TEXT:
                    await self.on_message(msg)
        except CONNECTION_ERRORS:
            logger.info("lost connection with websocket %s", self)
        finally:
            self.sockets.remove(self)
        return response

    def decode_message(self, msg: str) -> Any:
        """Decode JSON string message, override for different protocol"""
        try:
            return json.loads(msg)
        except json.JSONDecodeError:
            raise ProtocolError("JSON string expected") from None

    def encode_message(self, msg: Any) -> str:
        """Encode as JSON string message, override for different protocol"""
        try:
            return json.dumps(msg)
        except TypeError:
            raise ProtocolError("JSON object expected") from None

    async def on_message(self, msg):
        id_ = None
        rpc = None
        try:
            data = self.decode_message(msg.data)
            if not isinstance(data, dict):
                raise ProtocolError(
                    "Malformed message; expected dictionary, "
                    f"got {type(data).__name__}"
                )
            id_ = data.get("id")
            rpc = validated_schema(RpcProtocol, data)
            method = getattr(self, f"ws_rpc_{rpc.method}", None)
            if not method:
                raise ValidationErrors(
                    dict(method=f"{rpc.method} method not available")
                )
            response = await method(rpc.payload or {})
            await self.write(dict(id=rpc.id, method=rpc.method, response=response))
        except ProtocolError as exc:
            logger.error("Protocol error: %s", exc)
            await self.error_message(
                str(exc), id=id_, method=rpc.method if rpc else None
            )
        except ValidationErrors as exc:
            await self.error_message(
                "Invalid RPC parameters",
                errors=exc.errors,
                id=id_,
                method=rpc.method if rpc else None,
            )

    async def error_message(self, message, *, errors=None, **kw):
        error = dict(message=message)
        if errors:
            error["errors"] = errors
        await self.write(compact(error=error, **kw))

    async def write(self, msg: Dict) -> None:
        text = self.encode_message(msg)
        await self.response.send_str(text)

    async def close(self) -> None:
        await self.response.close()
        self.sockets.remove(self)
