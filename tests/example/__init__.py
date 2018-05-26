from openapi.middleware import json404

from .db import meta
from .endpoints import routes


def setup_app(app):
    meta(app['metadata'])
    app.middlewares.append(json404)
    app.router.add_routes(routes)
