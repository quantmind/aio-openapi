import uuid

from openapi import sentry
from openapi.middleware import json_error
from openapi.ws import Sockets, LocalBroker

from .db import meta
from .endpoints import routes
from .ws import ws_routes


def setup_app(app):
    meta(app['db'].metadata)
    app['broker'] = LocalBroker()
    app['web_sockets'] = Sockets(app)
    app.middlewares.append(json_error())
    app.middlewares.append(
        sentry.middleware(
            app, f'https://{uuid.uuid4().hex}@sentry.io/1234567', 'test'
        )
    )
    app.router.add_routes(routes)
    app.router.add_routes(ws_routes)
