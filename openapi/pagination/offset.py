from dataclasses import dataclass
from typing import Dict, NamedTuple, Optional, Type

from multidict import MultiDict
from yarl import URL

from openapi.data.fields import Choice, integer_field, str_field
from openapi.utils import docjoin

from .pagination import (
    DEF_PAGINATION_LIMIT,
    MAX_PAGINATION_LIMIT,
    Pagination,
    PaginationVisitor,
    from_filters_and_dataclass,
)


def offsetPagination(
    *order_by_fields: str,
    default_limit: int = DEF_PAGINATION_LIMIT,
    max_limit: int = MAX_PAGINATION_LIMIT,
) -> Type[Pagination]:
    """Crate a limit/offset :class:`.Pagination` dataclass"""
    if len(order_by_fields) == 0:
        raise ValueError("orderable_fields must be specified")

    @dataclass
    class OffsetPagination(Pagination):
        limit: int = integer_field(
            min_value=1,
            max_value=max_limit,
            default=default_limit,
            description="Limit the number of objects returned from the endpoint",
        )
        offset: int = integer_field(
            min_value=0,
            default=0,
            description=(
                "Number of objects to exclude. "
                "Use in conjunction with limit to paginate results"
            ),
        )
        order_by: str = str_field(
            validator=Choice(order_by_fields),
            default=order_by_fields[0],
            description=(
                "Order results by given column (default ascending order). "
                f"Possible values are {docjoin(order_by_fields)}"
            ),
        )

        def apply(self, visitor: PaginationVisitor) -> None:
            visitor.apply_offset_pagination(
                limit=self.limit, offset=self.offset, order_by=self.order_by
            )

        @classmethod
        def create_pagination(cls, data: dict) -> "OffsetPagination":
            return from_filters_and_dataclass(OffsetPagination, data)

        def links(
            self, url: URL, data: list, total: Optional[int] = None
        ) -> Dict[str, str]:
            """Return links for paginated data"""
            return Links(url=url, query=MultiDict(url.query)).links(
                total, self.limit, self.offset
            )

    return OffsetPagination


class Links(NamedTuple):
    url: URL
    query: MultiDict

    def first_link(self, total, limit, offset):
        n = self._count_part(offset, limit, 0)
        if n:
            offset -= n * limit
        if offset > 0:
            return self.link(0, min(limit, offset))

    def prev_link(self, total, limit, offset):
        if offset:
            olimit = min(limit, offset)
            prev_offset = offset - olimit
            return self.link(prev_offset, olimit)

    def next_link(self, total, limit, offset):
        next_offset = offset + limit
        if total > next_offset:
            return self.link(next_offset, limit)

    def last_link(self, total, limit, offset):
        n = self._count_part(total, limit, offset)
        if n > 0:
            return self.link(offset + n * limit, limit)

    def link(self, offset, limit):
        query = self.query.copy()
        query.update({"offset": offset, "limit": limit})
        return self.url.with_query(query)

    def _count_part(self, total, limit, offset):
        n = (total - offset) // limit
        # make sure we account for perfect matching
        if n * limit + offset == total:
            n -= 1
        return max(0, n)

    def links(self, total, limit, offset):
        links = {}
        first = self.first_link(total, limit, offset)
        if first:
            links["first"] = first
            links["prev"] = self.prev_link(total, limit, offset)
        next_ = self.next_link(total, limit, offset)
        if next_:
            links["next"] = next_
            links["last"] = self.last_link(total, limit, offset)
        return links
