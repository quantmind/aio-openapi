from aiohttp import web

from .exc import ImproperlyConfigured

try:
    from raven_aiohttp import AioHttpTransport
    from raven import Client
    from raven.conf.remote import RemoteConfig
except ImportError:  # pragma: no cover
    AioHttpTransport = None


def middleware(app, dsn, env="dev"):
    if not AioHttpTransport:  # pragma: no cover
        raise ImproperlyConfigured("Sentry middleware requires raven_aiohttp")
    app["sentry"] = Sentry(dsn, env)
    app.on_shutdown.append(close)

    @web.middleware
    async def middleware_handler(request, handler):
        try:
            return await handler(request)
        except Exception:
            content = await request.content.read()
            data = {
                "request": {
                    "url": str(request.url).split("?")[0],
                    "method": request.method.lower(),
                    "data": content,
                    "query_string": request.url.query_string,
                    "cookies": dict(request.cookies),
                    "headers": dict(request.headers),
                },
                "user": {"id": request.get("user_id")},
            }
            app["sentry"].captureException(data=data)
            raise

    return middleware_handler


async def close(app):
    await app["sentry"].close()


class Sentry:
    def __init__(self, dsn, env):
        client = Client(
            transport=AioHttpTransport, ignore_exceptions=[web.HTTPException]
        )
        client.remote = RemoteConfig(transport=AioHttpTransport)
        client._transport_cache = {None: client.remote}
        client.set_dsn(dsn, AioHttpTransport)
        self.env = env
        self.client = client

    def captureException(self, data=None):
        if data is None:
            data = {}
        data["environment"] = self.env
        self.client.captureException(data=data)

    async def close(self):
        transport = self.client.remote.get_transport()
        if transport:
            await transport.close()
