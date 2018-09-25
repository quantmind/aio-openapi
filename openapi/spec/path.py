from aiohttp import web

from multidict import MultiDict
from sqlalchemy.sql import Select

from openapi.json import loads, dumps
from ..data.dump import dump, dump_list
from ..data.validate import validate
from ..data.exc import ValidationErrors
from ..spec.pagination import Pagination, DEF_PAGINATION_LIMIT
from ..utils import compact, as_list


class ApiPath(web.View):
    """An OpenAPI path
    """
    path_schema = None
    private = False

    # UTILITIES

    def insert_data(self, data, *, strict=True, body_schema='body_schema'):
        data = self.cleaned(body_schema, data)
        if self.path_schema:
            path = self.cleaned('path_schema', self.request.match_info)
            data.update(path)
        return data

    def get_order_clause(self, table, query, order_by, order_desc):
        if not order_by:
            return query

        order_by_column = getattr(table.c, order_by)
        if order_desc:
            order_by_column = order_by_column.desc()
        return query.order_by(order_by_column)

    def limit_and_order_query(
            self,
            query,
            table,
            limit=DEF_PAGINATION_LIMIT,
            offset=0,
            order_by=None,
            order_desc=False,
    ):
        if isinstance(query, Select):
            query = self.get_order_clause(table, query, order_by, order_desc)
            query = query.offset(offset)
            query = query.limit(limit)
        return query

    def get_link_headers(self, url, limit_params):
        pag = Pagination(url)
        params = (
            limit_params['total'],
            limit_params['limit'],
            limit_params['offset'],
        )
        headers = pag.headers(*params)
        if headers:
            return {'Link': ', '.join(headers.values())}

    def get_limit_params(self, params):
        return dict(
            limit=params.pop('limit', DEF_PAGINATION_LIMIT),
            offset=params.pop('offset', 0),
            order_by=params.pop('order_by', None),
            order_desc=params.pop('order_desc', False),
        )

    def get_filters(self, *, query=None, query_schema='query_schema'):
        combined = MultiDict(query or ())
        combined.update(self.request.query)
        try:
            params = self.cleaned(query_schema, combined, multiple=True)
        except web.HTTPNotImplemented:
            params = {}
        if self.path_schema:
            path = self.cleaned('path_schema', self.request.match_info)
            params.update(path)
        return params

    def cleaned(
            self, schema, data, *, multiple=False, strict=True, Error=None):
        """Clean data for a given schema name
        """
        Schema = self.get_schema(schema)
        if isinstance(Schema, list):
            Schema = Schema[0]
        validated = validate(Schema, data, strict=strict, multiple=multiple)
        if validated.errors:
            if Error:
                raise Error()
            elif schema == 'path_schema':
                raise web.HTTPNotFound()
            self.raiseValidationError(errors=validated.errors)

        # Hacky hacky hack hack
        # Later we'll want to implement proper multicolumn search and so
        # this will be removed and will be included directly in the schema
        if hasattr(Schema, 'search_fields'):
            validated.data['search_fields'] = Schema.search_fields
        return validated.data

    def dump(self, schema, data):
        """Dump data using a given schema
        """
        if schema is None:
            return data
        Schema = self.get_schema(schema)
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

    def get_schema(self, schema: object) -> object:
        """Get the Schema class
        """
        if isinstance(schema, str):
            Schema = getattr(self.request['operation'], schema, None)
        else:
            Schema = schema
        if Schema is None:
            Schema = getattr(self, schema, None)
            if Schema is None:
                raise web.HTTPNotImplemented
        return Schema

    def raiseValidationError(self, message=None, errors=None):
        raw = compact(message=message, errors=as_list(errors or ()))
        data = self.dump(ValidationErrors, raw)
        raise web.HTTPUnprocessableEntity(**self.api_response_data(data))

    @classmethod
    def api_response_data(cls, data):
        return dict(
            body=dumps(data),
            content_type='application/json'
        )

    @classmethod
    def json_response(cls, data, **kwargs):
        return web.json_response(data, **kwargs, dumps=dumps)
