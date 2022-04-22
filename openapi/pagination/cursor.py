import base64
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple, Type

from dateutil.parser import parse as parse_date
from typing_extensions import TypedDict
from yarl import URL

from openapi import json
from openapi.data.fields import Choice, integer_field, str_field

from .pagination import (
    DEF_PAGINATION_LIMIT,
    MAX_PAGINATION_LIMIT,
    Pagination,
    PaginationVisitor,
    fields_no_sign,
    from_filters_and_dataclass,
)


class CursorType(TypedDict):
    order_by: str
    start: str
    limit: int
    previous: Optional[str]


def encode_cursor(data: Dict[str, str], previous: bool = False) -> str:
    cursor_bytes = json.dumps(dict(data=data, previous=previous)).encode("ascii")
    base64_bytes = base64.b64encode(cursor_bytes)
    return base64_bytes.decode("ascii")


def decode_cursor(cursor: Optional[str]) -> dict:
    if cursor:
        base64_bytes = cursor.encode("ascii")
        cursor_bytes = base64.b64decode(base64_bytes)
        return json.loads(cursor_bytes)
    return {}


def cursor_url(url: URL, cursor: str) -> URL:
    query = url.query.copy()
    query.update(_cursor=cursor)
    return url.with_query(query)


def flip_sign(field: str) -> str:
    return field[1:] if field.startswith("-") else f"-{field}"


def start_values(record: dict, fields: Tuple[str, ...]) -> Tuple[Tuple[str, str]]:
    """start values for pagination"""
    return tuple(
        (field, record[key]) for field, key in zip(fields, fields_no_sign(fields))
    )


def cursorPagination(
    *orderable_fields: str,
    desc: bool = False,
    default_limit: int = DEF_PAGINATION_LIMIT,
    max_limit: int = MAX_PAGINATION_LIMIT,
) -> Type[Pagination]:

    if len(orderable_fields) == 0:
        raise ValueError("orderable_fields must be specified")

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
            default="desc" if desc else "asc",
            description=("Order results descending or ascending"),
        )
        _cursor: str = ""
        _previous: str = ""

        def apply_page(self, visitor: PaginationVisitor) -> None:
            cursor = decode_cursor(self._cursor)
            visitor.apply_cursor_pagination(
                cursor.get("data", {}), self.limit, cursor.get("previous", False)
            )

        @classmethod
        def create_pagination(cls, data: dict) -> "CursorPagination":
            return from_filters_and_dataclass(CursorPagination, data)

        def links(
            self, url: URL, data: list, total: Optional[int] = None
        ) -> Dict[str, str]:
            links = {}
            if len(data) > self.limit:
                links["next"] = cursor_url(
                    url,
                    encode_cursor(start_values(data[self.limit], orderable_fields)),
                )
            if data:
                links["prev"] = cursor_url(
                    url,
                    encode_cursor(
                        start_values(
                            data[0], tuple(flip_sign(f) for f in orderable_fields)
                        ),
                        previous=True,
                    ),
                )
            return links

        def get_data(self, data: list) -> list:
            return data if len(data) <= self.limit else data[: self.limit]

    return CursorPagination


def cursor_to_python(py_type: Type, value) -> Any:
    if py_type is datetime:
        return parse_date(value)
    elif py_type is date:
        return parse_date(value).date()
    elif py_type is int:
        return int(value)
    else:
        return value
