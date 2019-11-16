import typing as t
from dataclasses import dataclass

from aiohttp.web import Application

from .cli import OpenApiClient
from .data.fields import Choice, IntegerValidator, bool_field, data_field, str_field
from .spec import OpenApi, OpenApiSpec
from .spec.pagination import MAX_PAGINATION_LIMIT
from .spec.utils import docjoin


def rest(
    openapi: t.Dict = None,
    setup_app: t.Callable[[Application], None] = None,
    base_path: str = "",
    commands: t.Optional[t.List] = None,
    allowed_tags: t.Optional[t.Set[str]] = None,
    validate_docs: bool = False,
    servers: t.Optional[t.List[str]] = None,
    OpenApiSpecClass: type = OpenApiSpec,
    **kwargs,
) -> OpenApiClient:
    """Create the OpenApi Client
    """
    return OpenApiClient(
        OpenApiSpecClass(
            OpenApi(**(openapi or {})),
            allowed_tags=allowed_tags,
            validate_docs=validate_docs,
            servers=servers,
        ),
        base_path=base_path,
        commands=commands,
        setup_app=setup_app,
        **kwargs,
    )


@dataclass
class Query:
    limit: int = data_field(
        validator=IntegerValidator(min_value=1, max_value=MAX_PAGINATION_LIMIT),
        description="Limit the number of objects returned from the endpoint",
    )
    offset: int = data_field(
        validator=IntegerValidator(min_value=0),
        description=(
            "Number of objects to exclude. "
            "Use in conjunction with limit to paginate results"
        ),
    )


def orderable(*orderable_fields) -> type:
    @dataclass
    class Orderable:
        order_by: str = data_field(
            validator=Choice(orderable_fields),
            description=(
                "Order results by given column (default ascending order). "
                f"Possible values are {docjoin(orderable_fields)}"
            ),
        )
        order_desc: bool = bool_field(
            description=("Change order direction to descending")
        )

    return Orderable


def searchable(*searchable_fields) -> type:
    """Create a dataclass for search fields
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
