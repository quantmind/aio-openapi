import os

from aiohttp import web

from .operation import op
from .path import ApiPath
from .spec import OpenApi, OpenApiSpec, SchemaParser, spec_root


__all__ = [
    'op', 'ApiPath', 'OpenApi', 'OpenApiSpec', 'SchemaParser', 'setup_app'
]

SPEC_ROUTE = os.environ.get('SPEC_ROUTE', '/spec')


def setup_app(app):
    if SPEC_ROUTE:
        app.add_routes(
            [
                web.get(SPEC_ROUTE, spec_root)
            ]
        )
