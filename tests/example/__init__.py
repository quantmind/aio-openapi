from openapi import sentry
from openapi.middleware import json404
from openapi.ws import Sockets, LocalBroker

from .db import meta
from .endpoints import routes
from .ws import ws_routes


def setup_app(app):
    meta(app['db'].metadata)
    app['broker'] = LocalBroker()
    app['web_sockets'] = Sockets(app)
    app.middlewares.append(sentry.middleware)
    app.middlewares.append(json404)
    app.router.add_routes(routes)
    app.router.add_routes(ws_routes)
