from typing import Any, Dict, Optional

from aiohttp import web
from multidict import MultiDict
from yarl import URL

from openapi.json import dumps, loads

from ..data.exc import ValidationErrors
from ..data.view import BAD_DATA_MESSAGE, DataView, ErrorType
from ..types import DataType, QueryType, SchemaTypeOrStr
from ..utils import compact
from . import hdrs


class ApiPath(web.View, DataView):
    """A :class:`.DataView` class for OpenAPI path
    """

    path_schema: Optional[type] = None
    """Optional dataclass for validating path variables"""
    private: bool = False

    # UTILITIES

    def insert_data(
        self,
        data: DataType,
        *,
        strict: bool = True,
        body_schema: SchemaTypeOrStr = "body_schema",
    ) -> Dict[str, Any]:
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
        """Collect a dictionary of filters. If :attr:`path_schema` is defined,
        collect filter data from there as well.

        :param query: query dictionary (will be overwritten by the request.query)
        :param query_schema: a dataclass or an the name of an attribute in Operation
            for collecting query filters
        """
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

    async def json_data(self) -> DataType:
        """Load JSON data from the request.

        :raise HTTPBadRequest: when body data is not valid JSON
        """
        try:
            return await self.request.json(loads=loads)
        except Exception:
            raise web.HTTPBadRequest(
                **self.api_response_data({"message": "Invalid JSON payload"})
            )

    def raiseValidationError(self, message: str = "", errors: ErrorType = None) -> None:
        raw = self.as_errors(message, errors)
        data = self.dump(ValidationErrors, raw)
        raise web.HTTPUnprocessableEntity(**self.api_response_data(data))

    def raise_bad_data(
        self, exc: Optional[Exception] = None, message: str = ""
    ) -> None:
        raw = compact(message=message or BAD_DATA_MESSAGE)
        data = self.dump(ValidationErrors, raw)
        raise web.HTTPBadRequest(**self.api_response_data(data))

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
