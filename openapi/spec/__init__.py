import os

from aiohttp import web

from .operation import op
from .path import ApiPath
from .spec import OpenApi, OpenApiSpec, SchemaParser, spec_root
from ..data.exc import Error


__all__ = [
    'op', 'ApiPath', 'OpenApi', 'OpenApiSpec', 'SchemaParser', 'setup_app'
]

SPEC_ROUTE = os.environ.get('SPEC_ROUTE', '/spec')


def setup_app(app):
    app['exc_schema'] = Error
    if SPEC_ROUTE:
        app.add_routes(
            [
                web.get('/spec', spec_root)
            ]
        )
