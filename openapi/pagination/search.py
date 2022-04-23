from dataclasses import dataclass
from typing import Sequence

from openapi.data.fields import str_field
from openapi.utils import docjoin

from .pagination import from_filters_and_dataclass


class SearchVisitor:
    def apply_search(self, search: str, search_fields: Sequence[str]) -> None:
        raise NotImplementedError


@dataclass
class Search:
    @classmethod
    def create_search(cls, data: dict) -> "Search":
        return cls()

    def apply(self, visitor: SearchVisitor) -> None:
        pass


def searchable(*searchable_fields) -> type:
    """Create a dataclass with `search_fields` class attribute and `search` field.
    The search field is a set of field which can be used for searching and it is used
    internally by the library, while the `search` field is the query string passed
    in the url.

    :param searchable_fields: fields which can be used for searching
    """
    fields = docjoin(searchable_fields)

    @dataclass
    class Searchable(Search):
        search_fields = frozenset(searchable_fields)
        search: str = str_field(
            description=(
                "Search query string. " f"The search is performed on {fields} fields."
            )
        )

        @classmethod
        def create_search(cls, data: dict) -> "Searchable":
            return from_filters_and_dataclass(Searchable, data)

        def apply(self, visitor: SearchVisitor) -> None:
            visitor.apply_search(self.search, self.search_fields)

    return Searchable
