import time
import asyncio
import hashlib
import logging
from typing import Dict
from dataclasses import dataclass

from aiohttp import web

from ..data import fields
from ..data.validate import validated_schema, ValidationErrors
from ..utils import compact
from .. import json
from .channels import Channels


logger = logging.getLogger('openapi.ws')


@dataclass
class RpcProtocol:
    id: str = fields.data_field(required=True)
    method: str = fields.data_field(required=True)
    payload: Dict = None


class ProtocolError(RuntimeError):
    pass


class WsPathMixin:
    """Api Path mixin for Websocket RPC protocol
    """
    SOCKETS_KEY = 'web_sockets'

    @property
    def sockets(self):
        """Connected websockets
        """
        return self.request.app.get(self.SOCKETS_KEY)

    @property
    def channels(self):
        """Channels for pub/sub
        """
        sockets = self.sockets
        return sockets.channels if sockets else None

    async def get(self):
        response = web.WebSocketResponse()
        available = response.can_prepare(self.request)
        if not available:
            raise web.HTTPBadRequest(**self.api_response_data({
                'message': 'Unable to open websocket connection'
            }))
        await response.prepare(self.request)
        self.response = response
        self.started = time.time()
        key = '%s - %s' % (self.request.remote, self.started)
        self.socket_id = hashlib.sha224(key.encode('utf-8')).hexdigest()
        #
        # Add to set of sockets if available
        sockets = self.sockets
        if sockets:
            sockets.add(self)
        #
        async for msg in response:
            if msg.type == web.WSMsgType.TEXT:
                await self.on_message(msg)

        return response

    def decode_message(self, msg):
        """Decode JSON string message, override for different protocol
        """
        try:
            return json.loads(msg)
        except json.JSONDecodeError:
            raise ProtocolError('JSON string expected') from None

    def encode_message(self, msg):
        """Encode as JSON string message, override for different protocol
        """
        try:
            return json.dumps(msg)
        except json.JSONDecodeError:
            raise ProtocolError('JSON object expected') from None

    async def on_message(self, msg):
        id_ = None
        rpc = None
        try:
            data = self.decode_message(msg.data)
            if not isinstance(data, dict):
                raise ProtocolError('Malformed message; expected dictionary, '
                                    f'got {type(data).__name__}')
            id_ = data.get('id')
            rpc = validated_schema(RpcProtocol, data)
            method = getattr(self, f'ws_rpc_{rpc.method}', None)
            if not method:
                raise ValidationErrors(
                    dict(method=f'{rpc.method} method not available')
                )
            response = await method(rpc.payload or {})
            await self.write(dict(
                id=rpc.id,
                method=rpc.method,
                response=response
            ))
        except ProtocolError as exc:
            logger.error('Protocol error: %s', exc)
            await self.error_message(str(exc))
        except ValidationErrors as exc:
            await self.error_message(
                'Invalid RPC parameters',
                errors=exc.errors,
                id=id_,
                method=rpc.method if rpc else None
            )

    async def error_message(self, message, *, errors=None, **kw):
        error = dict(message=message)
        if errors:
            error['errors'] = errors
        await self.write(compact(error=error, **kw))

    async def write(self, msg: Dict) -> None:
        try:
            text = self.encode_message(msg)
            await self.response.send_str(text)
        except RuntimeError:
            # TODO: is this the best way to avoid spamming exception
            #       when the websocket is closed by the client?
            pass


class Sockets:

    def __init__(self, app, **kwargs):
        self.sockets = set()
        self.channels = Channels(app.get('broker'), **kwargs)
        app.on_startup.append(self.start)
        app.on_shutdown.append(self.close)
        app['channels'] = self.channels

    def add(self, ws):
        self.sockets.add(ws)

    async def start(self, app):
        await self.channels.start()

    async def close(self, app):
        await self.channels.close()
        await asyncio.gather(*[view.response.close() for view in self.sockets])
        self.sockets.clear()
