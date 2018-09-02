from openapi.middleware import json404
from openapi.ws import Sockets

from .db import meta
from .endpoints import routes
from .ws import ws_routes, LocalPubSub


def setup_app(app):
    meta(app['db'].metadata)
    app['broker'] = LocalPubSub()
    app['web_sockets'] = Sockets(app)
    app.middlewares.append(json404)
    app.router.add_routes(routes)
    app.router.add_routes(ws_routes)
