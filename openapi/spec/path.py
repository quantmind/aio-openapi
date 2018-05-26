from aiohttp import web

from openapi.json import loads, dumps
from ..data.dump import dump, dump_list
from ..data.validate import validate


class ApiPath(web.View):
    """An OpenAPI path
    """
    path_schema = None

    # UTILITIES

    def cleaned(self, name, data):
        """Clean data for a given schema name
        """
        Schema = getattr(self.request['operation'], name, None)
        if Schema is None:
            Schema = getattr(self, name, None)
            if Schema is None:
                raise web.HTTPNotImplemented
        # if isinstance(Schema, list):
        #     Schema = Schema[0]
        schema = validate(Schema, data)
        if schema.errors:
            app = self.request.app
            errors = app['exc_schema'].from_errors(schema.errors)
            raise web.HTTPUnprocessableEntity(**self.api_response_data(errors))
        return schema.data

    def dump(self, name, data):
        """call clean for now"""
        Schema = getattr(self.request['operation'], name, None)
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

    def api_response_data(self, data):
        return dict(
            body=dumps(data),
            content_type='application/json'
        )

    def json_response(self, data, **kwargs):
        return web.json_response(data, **kwargs, dumps=dumps)
