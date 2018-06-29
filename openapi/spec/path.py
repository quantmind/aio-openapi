from aiohttp import web

from openapi.json import loads, dumps
from ..data.dump import dump, dump_list
from ..data.validate import validate


class ApiPath(web.View):
    """An OpenAPI path
    """
    path_schema = None
    private = False

    # UTILITIES

    def insert_data(self, data, strict=True):
        data = self.cleaned('body_schema', data)
        if self.path_schema:
            path = self.cleaned('path_schema', self.request.match_info)
            data.update(path)
        return data

    def get_filters(self, query=None, query_schema='query_schema'):
        combined = dict(self.request.query)
        combined.update(query or {})
        try:
            params = self.cleaned(query_schema, combined)
        except web.HTTPNotImplemented:
            params = {}
        if self.path_schema:
            path = self.cleaned('path_schema', self.request.match_info)
            params.update(path)
        return params

    def cleaned(self, name, data, strict=True):
        """Clean data for a given schema name
        """
        Schema = getattr(self.request['operation'], name, None)
        if Schema is None:
            Schema = getattr(self, name, None)
            if Schema is None:
                raise web.HTTPNotImplemented
        if isinstance(Schema, list):
            Schema = Schema[0]
        schema = validate(Schema, data, strict)
        if schema.errors:
            if name == 'path_schema':
                raise web.HTTPNotFound()
            app = self.request.app
            errors = app['exc_schema'].from_errors(schema.errors)
            raise web.HTTPUnprocessableEntity(**self.api_response_data(errors))
        return schema.data

    def dump(self, schema, data):
        """Dump data using a given schema
        """
        if isinstance(schema, str):
            Schema = getattr(self.request['operation'], schema, None)
        else:
            Schema = schema
        if Schema is None:
            raise web.HTTPNotImplemented
        if isinstance(Schema, list):
            Schema = Schema[0]
            return dump_list(Schema, data)
        else:
            return dump(Schema, data)

    async def json_data(self):
        """Load JSON data from the request
        """
        try:
            return await self.request.json(loads=loads)
        except Exception:
            raise web.HTTPBadRequest(
                **self.api_response_data({'message': 'Invalid JSON payload'})
            )

    @classmethod
    def api_response_data(cls, data):
        return dict(
            body=dumps(data),
            content_type='application/json'
        )

    @classmethod
    def json_response(cls, data, **kwargs):
        return web.json_response(data, **kwargs, dumps=dumps)
