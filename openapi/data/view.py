import os
from dataclasses import dataclass
from typing import Any, Dict, NoReturn, Optional, cast

from aiohttp import web

from ..types import DataType, QueryType, StrDict
from ..utils import TypingInfo, as_list, compact
from .dump import dump
from .pagination import DEF_PAGINATION_LIMIT
from .validate import ErrorType, ValidationErrors, validate

BAD_DATA_MESSAGE = os.getenv("BAD_DATA_MESSAGE", "Invalid data format")


@dataclass
class Operation:
    body_schema: Optional[TypingInfo] = None
    query_schema: Optional[TypingInfo] = None
    response_schema: Optional[TypingInfo] = None
    response: int = 200


class DataView:
    """Utility class for data with a valid :ref:`aio-openapi-schema`"""

    operation: Operation = Operation()

    def cleaned(
        self,
        schema: Any,
        data: QueryType,
        *,
        multiple: bool = False,
        strict: bool = True,
        Error: Optional[type] = None,
    ) -> DataType:
        """Clean data using a given schema

        :param schema: a valid :ref:`aio-openapi-schema` or an the name of an
            attribute in :class:`.Operation`
        :param data: data to validate and clean
        :param multiple: multiple values for a given key are acceptable
        :param strict: all required attributes in schema must be available
        :param Error: optional :class:`.Exception` class
        """
        type_info = self.get_schema(schema)
        validated = validate(type_info, data, strict=strict, multiple=multiple)
        if validated.errors:
            if Error:
                raise Error
            elif schema == "path_schema":
                raise web.HTTPNotFound
            self.raise_validation_error(errors=validated.errors)

        # Hacky hacky hack hack
        # Later we'll want to implement proper multicolumn search and so
        # this will be removed and will be included directly in the schema
        search_fields = getattr(type_info.element, "search_fields", None)
        if search_fields:
            validated.data["search_fields"] = search_fields
        return validated.data

    def dump(self, schema: Any, data: DataType) -> DataType:
        """Dump data using a given a valid :ref:`aio-openapi-schema`,
        if the schema is `None` it returns the same `data` as the input.

        :param schema: a schema or an the name of an attribute in :class:`.Operation`
        :param data: data to clean and dump
        """
        return data if schema is None else dump(self.get_schema(schema), data)

    def get_schema(self, schema: Any = None) -> TypingInfo:
        """Get the :ref:`aio-openapi-schema`. If not found it raises an exception

        :param schema: a schema or an the name of an attribute in :class:`.Operation`
        """
        if isinstance(schema, str):
            Schema = getattr(self.operation, schema, None)
        else:
            Schema = schema
        if Schema is None:
            Schema = getattr(self, str(schema), None)
            if Schema is None:
                raise web.HTTPNotImplemented
        return cast(TypingInfo, TypingInfo.get(Schema))

    def get_special_params(self, params: StrDict) -> StrDict:
        """A dictionary of special parameters extracted from `params`.
        This function has side effects on params.

        :param params: dictionary from where special parameters are extracted
        """
        return dict(
            limit=params.pop("limit", DEF_PAGINATION_LIMIT),
            offset=params.pop("offset", 0),
            order_by=params.pop("order_by", None),
            order_desc=params.pop("order_desc", False),
            search=params.pop("search", None),
            search_fields=params.pop("search_fields", []),
        )

    def validation_error(
        self, message: str = "", errors: Optional[ErrorType] = None
    ) -> Exception:
        """Create the validation exception used by :meth:`.raise_validation_error`"""
        return ValidationErrors(self.as_errors(message, errors))

    def raise_validation_error(
        self, message: str = "", errors: Optional[ErrorType] = None
    ) -> NoReturn:
        """Raise an :class:`aiohttp.web.HTTPUnprocessableEntity`"""
        raise self.validation_error(message, errors)

    def raise_bad_data(
        self, exc: Optional[Exception] = None, message: str = ""
    ) -> None:
        if not message and exc:
            raise exc from exc
        raise TypeError(message or BAD_DATA_MESSAGE)

    def as_errors(self, message: str = "", errors: Optional[ErrorType] = None) -> Dict:
        if isinstance(errors, str):
            message = cast(str, message or errors)
            errors = None
        return compact(message=message, errors=as_list(errors or ()))
