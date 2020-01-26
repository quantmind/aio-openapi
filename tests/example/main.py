import uuid

from aiohttp import web

from openapi import sentry
from openapi.db import get_db
from openapi.middleware import json_error
from openapi.rest import rest
from openapi.ws import LocalBroker, Sockets

from .db import meta
from .endpoints import routes
from .ws import ws_routes


def setup_app(app: web.Application) -> None:
    db = get_db(app)
    meta(db.metadata)
    app["broker"] = LocalBroker()
    app["web_sockets"] = Sockets(app)
    app.middlewares.append(json_error())
    app.middlewares.append(
        sentry.middleware(app, f"https://{uuid.uuid4().hex}@sentry.io/1234567", "test")
    )
    app.router.add_routes(routes)
    app.router.add_routes(ws_routes)


def create_app():
    return rest(setup_app=setup_app)


if __name__ == "__main__":
    create_app().main()
