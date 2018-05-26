from .db import meta
from .endpoints import routes


def setup_app(app):
    meta(app['metadata'])
    app.router.add_routes(routes)
