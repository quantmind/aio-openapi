from typing import Any, Dict, List, Optional, Union, cast

from aiohttp import web
from multidict import MultiDict
from yarl import URL

from openapi.json import dumps, loads

from ..data.dump import dump, dump_list
from ..data.exc import ValidationErrors
from ..data.validate import validate
from ..utils import as_list, compact
from . import hdrs

SchemaType = Union[List[type], type]
SchemaTypeOrStr = Union[str, SchemaType]
StrDict = Dict[str, Any]
QueryType = Union[StrDict, MultiDict]
DataType = Union[List[StrDict], StrDict]


class ApiPath(web.View):
    """An OpenAPI path
    """

    path_schema: Optional[type] = None
    private: bool = False

    # UTILITIES

    def insert_data(
        self, data, *, strict: bool = True, body_schema: SchemaTypeOrStr = "body_schema"
    ):
        data = self.cleaned(body_schema, data)
        if self.path_schema:
            path = self.cleaned("path_schema", self.request.match_info)
            data.update(path)
        return data

    def get_filters(
        self,
        *,
        query: Optional[QueryType] = None,
        query_schema: SchemaTypeOrStr = "query_schema",
    ) -> Dict[str, Any]:
        """Collect a dictionary of filters"""
        combined = MultiDict(query or ())
        combined.update(self.request.query)
        try:
            params = self.cleaned(query_schema, combined, multiple=True)
        except web.HTTPNotImplemented:
            params = {}
        if self.path_schema:
            path = self.cleaned("path_schema", self.request.match_info)
            params.update(path)
        return params

    def cleaned(
        self,
        schema: SchemaTypeOrStr,
        data: QueryType,
        *,
        multiple: bool = False,
        strict: bool = True,
        Error: type = None,
    ) -> StrDict:
        """Clean data for a given schema name
        """
        Schema = self.get_schema(schema)
        if isinstance(Schema, list):
            Schema = Schema[0]
        validated = validate(Schema, data, strict=strict, multiple=multiple)
        if validated.errors:
            if Error:
                raise Error
            elif schema == "path_schema":
                raise web.HTTPNotFound
            self.raiseValidationError(errors=validated.errors)

        # Hacky hacky hack hack
        # Later we'll want to implement proper multicolumn search and so
        # this will be removed and will be included directly in the schema
        if hasattr(Schema, "search_fields"):
            validated.data["search_fields"] = Schema.search_fields
        return validated.data

    def dump(
        self, schema: Optional[SchemaTypeOrStr], data: DataType
    ) -> Optional[DataType]:
        """Dump data using a given schema, if the schema is `None` it returns the
        same `data` as the input
        """
        if schema is None:
            return data
        Schema = self.get_schema(schema)
        if isinstance(Schema, list):
            Schema = Schema[0]
            return dump_list(Schema, cast(List[Dict], data))
        else:
            return dump(Schema, cast(Dict, data))

    async def json_data(self) -> DataType:
        """Load JSON data from the request
        """
        try:
            return await self.request.json(loads=loads)
        except Exception:
            raise web.HTTPBadRequest(
                **self.api_response_data({"message": "Invalid JSON payload"})
            )

    def get_schema(self, schema: Optional[SchemaTypeOrStr] = None) -> SchemaType:
        """Get the Schema dataclass
        """
        if isinstance(schema, str):
            Schema = getattr(self.request["operation"], schema, None)
        else:
            Schema = schema
        if Schema is None:
            Schema = getattr(self, str(schema), None)
            if Schema is None:
                raise web.HTTPNotImplemented
        return Schema

    def raiseValidationError(self, message=None, errors=None) -> None:
        raw = compact(message=message, errors=as_list(errors or ()))
        data = self.dump(ValidationErrors, raw)
        raise web.HTTPUnprocessableEntity(**self.api_response_data(data))

    def full_url(self) -> URL:
        return full_url(self.request)

    @classmethod
    def api_response_data(cls, data: DataType) -> Dict[str, Any]:
        return dict(body=dumps(data), content_type="application/json")

    @classmethod
    def json_response(cls, data, **kwargs):
        kwargs.setdefault("dumps", dumps)
        return web.json_response(data, **kwargs)


def full_url(request) -> URL:
    headers = request.headers
    proto = headers.get(hdrs.X_FORWARDED_PROTO)
    host = headers.get(hdrs.X_FORWARDED_HOST)
    port = headers.get(hdrs.X_FORWARDED_PORT)
    if proto and host:
        url = URL.build(scheme=proto, host=host)
        if port:
            port = int(port)
            if url.port != port:
                url = url.with_port(port)
        return url.join(request.rel_url)
    else:
        return request.url
