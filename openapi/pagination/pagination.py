import os
from dataclasses import dataclass, fields
from typing import (
    Dict,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from aiohttp import web
from yarl import URL

from openapi.json import dumps

MAX_PAGINATION_LIMIT: int = int(os.environ.get("MAX_PAGINATION_LIMIT") or 100)
DEF_PAGINATION_LIMIT: int = int(os.environ.get("DEF_PAGINATION_LIMIT") or 50)


class PaginationVisitor:
    """Visitor for pagination"""

    def apply_offset_pagination(
        self, limit: int, offset: int, order_by: Union[str, List[str]]
    ):
        raise NotImplementedError

    def apply_cursor_pagination(
        self,
        cursor: Sequence[Tuple[str, str]],
        limit: int,
        order_by: Sequence[str],
        previous: bool,
    ):
        raise NotImplementedError


T = TypeVar("T")


def from_filters_and_dataclass(data_class: Type[T], data: dict) -> T:
    params = {}
    for field in fields(data_class):
        if field.name in data:
            params[field.name] = data.pop(field.name)
    return data_class(**params)


def fields_no_sign(fields: Sequence[str]) -> Tuple[str, ...]:
    return tuple(field[1:] if field.startswith("-") else field for field in fields)


def fields_flip_sign(fields: Sequence[str]) -> Tuple[str, ...]:
    return tuple(flip_field_sign(field) for field in fields)


def flip_field_sign(field: str) -> str:
    return field[1:] if field.startswith("-") else f"-{field}"


@dataclass
class Pagination:
    @classmethod
    def create_pagination(cls, data: dict) -> "Pagination":
        return cls()

    def apply(self, visitor: PaginationVisitor) -> None:
        """Apply pagination to the visitor"""
        pass

    def paginated(
        self, url: URL, data: list, total: Optional[int] = None
    ) -> "PaginatedData":
        """Return paginated data"""
        return PaginatedData(url=url, data=data, pagination=self, total=total)

    def links(
        self, url: URL, data: list, total: Optional[int] = None
    ) -> Dict[str, str]:
        """Return links for paginated data"""
        return {}

    def get_data(self, data: list) -> list:
        return data


class PaginatedData(NamedTuple):
    url: URL
    data: list
    pagination: Pagination
    total: Optional[int] = None

    def json_response(self, headers: Optional[Dict[str, str]] = None, **kwargs):
        headers = headers or {}
        links = self.header_links()
        if links:
            headers["Link"] = links
        if self.total is not None:
            headers["X-Total-Count"] = str(self.total)
        kwargs.setdefault("dumps", dumps)
        return web.json_response(
            self.pagination.get_data(self.data), headers=headers, **kwargs
        )

    def header_links(self) -> str:
        links = self.pagination.links(self.url, self.data, self.total)
        return ", ".join(f'<{value}>; rel="{name}"' for name, value in links.items())
