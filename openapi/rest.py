from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from aiohttp.web import Application

from .cli import OpenApiClient
from .data.fields import Choice, integer_field, str_field
from .data.pagination import MAX_PAGINATION_LIMIT
from .spec import OpenApi, OpenApiSpec, Redoc
from .spec.utils import docjoin


def rest(
    openapi: Optional[Dict] = None,
    setup_app: Callable[[Application], None] = None,
    base_path: str = "",
    commands: Optional[List] = None,
    allowed_tags: Sequence[str] = (),
    validate_docs: bool = False,
    servers: Optional[List[str]] = None,
    security: Optional[Dict[str, Dict]] = None,
    redoc: Optional[Redoc] = None,
    OpenApiSpecClass: type = OpenApiSpec,
    **kwargs,
) -> OpenApiClient:
    """Create the OpenApi Client"""
    if openapi is not None:
        openapi = OpenApiSpecClass(
            OpenApi(**(openapi or {})),
            allowed_tags=allowed_tags,
            validate_docs=validate_docs,
            servers=servers,
            security=security,
            redoc=redoc,
        )
    return OpenApiClient(
        spec=openapi,
        base_path=base_path,
        commands=commands,
        setup_app=setup_app,
        **kwargs,
    )


@dataclass
class Query:
    """Base dataclass for querying pagination"""

    limit: int = integer_field(
        min_value=1,
        max_value=MAX_PAGINATION_LIMIT,
        description="Limit the number of objects returned from the endpoint",
    )
    offset: int = integer_field(
        min_value=0,
        description=(
            "Number of objects to exclude. "
            "Use in conjunction with limit to paginate results"
        ),
    )


def orderable(*orderable_fields) -> type:
    """Create a dataclass with `order_by` choice field and the `order_desc`
    boolean field.

    :param *orderable_fields: fields which can be used for ordering
    """

    @dataclass
    class Orderable:
        order_by: str = str_field(
            validator=Choice(orderable_fields),
            description=(
                "Order results by given column (default ascending order). "
                f"Possible values are {docjoin(orderable_fields)}"
            ),
        )

    return Orderable


def searchable(*searchable_fields) -> type:
    """Create a dataclass with `search_fields` class attribute and `search` field.
    The search field is a set of field which can be used for searching and it is used
    internally by the library, while the `search` field is the query string passed
    in the url.

    :param searchable_fields: fields which can be used for searching
    """
    fields = docjoin(searchable_fields)

    @dataclass
    class Searchable:
        search_fields = frozenset(searchable_fields)
        search: str = str_field(
            description=(
                "Search query string. " f"The search is performed on {fields} fields."
            )
        )

    return Searchable
