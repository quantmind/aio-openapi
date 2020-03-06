import uuid

from aiohttp import web

from openapi import sentry
from openapi.db import get_db
from openapi.middleware import json_error
from openapi.rest import rest
from openapi.ws import LocalBroker, Sockets

from .db import meta
from .db_additional import additional_meta
from .endpoints import routes
from .endpoints_additional import additional_routes
from .endpoints_base import base_routes
from .ws import ws_routes


def create_app():
    return rest(
        security=dict(
            auth_key={
                "type": "apiKey",
                "name": "X-Meta-Api-Key",
                "description": (
                    "The authentication key is required to access most "
                    "endpoints of the API"
                ),
                "in": "header",
            }
        ),
        setup_app=setup_app,
        # validate_docs=True
    )


def setup_app(app: web.Application) -> None:
    db = get_db(app)
    meta(db.metadata)
    app.middlewares.append(json_error())
    app.middlewares.append(
        sentry.middleware(app, f"https://{uuid.uuid4().hex}@sentry.io/1234567", "test")
    )
    app.router.add_routes(base_routes)
    app.router.add_routes(routes)
    #
    # Additional routes for testing
    additional_meta(db.metadata)
    app.router.add_routes(additional_routes)
    app["broker"] = LocalBroker()
    app["web_sockets"] = Sockets(app)
    app.router.add_routes(ws_routes)


if __name__ == "__main__":
    create_app().main()
