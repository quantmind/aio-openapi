import uuid

from aiohttp import web

from openapi.db.commands import db as db_command
from openapi.middleware import json_error, sentry_middleware
from openapi.rest import rest
from openapi.spec import Redoc

from . import db
from .endpoints import routes
from .endpoints_additional import additional_routes
from .endpoints_base import base_routes
from .endpoints_cursor import series_routes
from .endpoints_form import form_routes
from .ws import LocalBroker, ws_routes


def create_app():
    return rest(
        openapi=dict(title="Test API"),
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
        commands=[db_command],
        redoc=Redoc(),
    )


def setup_app(app: web.Application) -> None:
    db.setup(app)
    app.middlewares.append(json_error())
    sentry_middleware(app, f"https://{uuid.uuid4().hex}@sentry.io/1234567", "test")
    app.router.add_routes(base_routes)
    app.router.add_routes(routes)
    app.router.add_routes(series_routes)
    #
    # Additional routes for testing
    app.router.add_routes(additional_routes)
    app.router.add_routes(form_routes)
    app["web_sockets"] = LocalBroker.for_app(app)
    app.router.add_routes(ws_routes)


if __name__ == "__main__":
    create_app().main()
