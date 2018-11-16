import asyncio

from aiohttp import web
from raven import Client
from raven.conf.remote import RemoteConfig
from raven_aiohttp import AioHttpTransport

client = Client(
    transport=AioHttpTransport,
    ignore_exceptions=[web.HTTPException],
)


def disable():
    client.remote = RemoteConfig(transport=AioHttpTransport)
    client._transport_cache = {
        None: client.remote
    }


disable()
context_processor = None
environment = None


def setup(dsn, environment_):
    global environment
    environment = environment_
    client.set_dsn(dsn, AioHttpTransport)


def add_context_processor(processor):
    global context_processor
    context_processor = processor


def captureException(*args, **kwargs):
    """shortcut"""
    data = kwargs.setdefault('data', {})
    data['environment'] = environment
    return client.captureException(*args, **kwargs)


@web.middleware
async def middleware(request, handler):
    try:
        return await handler(request)
    except Exception:
        content = await request.content.read()
        data = {
            'environment': environment,
            'request': {
                'url': str(request.url).split('?')[0],
                'method': request.method.lower(),
                'data': content,
                'query_string': request.url.query_string,
                'cookies': dict(request.cookies),
                'headers': dict(request.headers),
            },
            'user': {
                'id': request.get('user_id'),
            }
        }
        if context_processor is not None:
            data = context_processor(data, request)
            if asyncio.iscoroutine(data):
                data = await data
        client.captureException(data=data)
        raise


async def close(*args, **kwargs):
    transport = client.remote.get_transport()
    if transport:
        await transport.close()
