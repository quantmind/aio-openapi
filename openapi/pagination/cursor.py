import base64
from dataclasses import dataclass
from datetime import date, datetime
from functools import cached_property
from typing import Any, Dict, Optional, Tuple, Type

from dateutil.parser import parse as parse_date
from yarl import URL

from openapi import json
from openapi.data.fields import Choice, integer_field, str_field
from openapi.data.validate import ValidationErrors

from .pagination import (
    DEF_PAGINATION_LIMIT,
    MAX_PAGINATION_LIMIT,
    Pagination,
    PaginationVisitor,
    fields_flip_sign,
    fields_no_sign,
    from_filters_and_dataclass,
)

CursorType = Tuple[Tuple[str, str], ...]


def encode_cursor(data: Tuple[str, ...], previous: bool = False) -> str:
    cursor_bytes = json.dumps((data, previous)).encode("ascii")
    base64_bytes = base64.b64encode(cursor_bytes)
    return base64_bytes.decode("ascii")


def decode_cursor(
    cursor: Optional[str], field_names: Tuple[str]
) -> Tuple[CursorType, bool]:
    try:
        if cursor:
            base64_bytes = cursor.encode("ascii")
            cursor_bytes = base64.b64decode(base64_bytes)
            values, previous = json.loads(cursor_bytes)
            if len(values) == len(field_names):
                return tuple(zip(field_names, values)), previous
            raise ValueError
        return (), False
    except Exception as e:
        raise ValidationErrors("invalid cursor") from e


def cursor_url(url: URL, cursor: str) -> URL:
    query = url.query.copy()
    query.update(_cursor=cursor)
    return url.with_query(query)


def start_values(record: dict, field_names: Tuple[str, ...]) -> Tuple[str, ...]:
    """start values for pagination"""
    return tuple(record[field] for field in field_names)


def cursorPagination(
    *order_by_fields: str,
    default_limit: int = DEF_PAGINATION_LIMIT,
    max_limit: int = MAX_PAGINATION_LIMIT,
) -> Type[Pagination]:

    if len(order_by_fields) == 0:
        raise ValueError("orderable_fields must be specified")

    field_names = fields_no_sign(order_by_fields)

    @dataclass
    class CursorPagination(Pagination):
        limit: int = integer_field(
            min_value=1,
            max_value=max_limit,
            default=default_limit,
            required=False,
            description="Limit the number of objects returned from the endpoint",
        )
        direction: str = str_field(
            validator=Choice(("asc", "desc")),
            required=False,
            default="asc",
            description=(
                f"Sort results via `{', '.join(order_by_fields)}` "
                "in descending or ascending order"
            ),
        )
        _cursor: str = str_field(default="", hidden=True)

        @cached_property
        def cursor_info(self) -> Tuple[CursorType, Tuple[str, ...], bool]:
            order_by = (
                fields_flip_sign(order_by_fields)
                if self.direction == "desc"
                else order_by_fields
            )
            cursor, previous = decode_cursor(self._cursor, order_by)
            return cursor, order_by, previous

        @property
        def previous(self) -> bool:
            return self.cursor_info[2]

        def apply(self, visitor: PaginationVisitor) -> None:
            cursor, order_by, previous = self.cursor_info
            visitor.apply_cursor_pagination(
                cursor,
                self.limit,
                order_by,
                previous=previous,
            )

        @classmethod
        def create_pagination(cls, data: dict) -> "CursorPagination":
            return from_filters_and_dataclass(CursorPagination, data)

        def links(
            self, url: URL, data: list, total: Optional[int] = None
        ) -> Dict[str, str]:
            links = {}
            if self.previous:
                if len(data) > self.limit + 1:
                    links["prev"] = cursor_url(
                        url,
                        encode_cursor(
                            start_values(data[self.limit], field_names), previous=True
                        ),
                    )
                if self._cursor:
                    links["next"] = cursor_url(
                        url,
                        encode_cursor(
                            start_values(data[0], field_names),
                        ),
                    )
            else:
                if len(data) > self.limit:
                    links["next"] = cursor_url(
                        url,
                        encode_cursor(start_values(data[self.limit], field_names)),
                    )
                if self._cursor:
                    links["prev"] = cursor_url(
                        url,
                        encode_cursor(
                            start_values(data[0], field_names),
                            previous=True,
                        ),
                    )
            return links

        def get_data(self, data: list) -> list:
            if self.previous:
                data = list(reversed(data[1:]))
                return data if len(data) <= self.limit else data[1:]
            return data if len(data) <= self.limit else data[: self.limit]

    return CursorPagination


def cursor_to_python(py_type: Type, value: Any) -> Any:
    try:
        if py_type is datetime:
            return parse_date(value)
        elif py_type is date:
            return parse_date(value).date()
        elif py_type is int:
            return int(value)
        else:
            return value
    except Exception as e:
        raise ValidationErrors("invalid cursor") from e
