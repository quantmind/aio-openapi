import typing
from dataclasses import dataclass

from .cli import OpenApiClient
from .data.fields import Choice, IntegerValidator, bool_field, data_field, str_field
from .spec import OpenApi, OpenApiSpec
from .spec.pagination import MAX_PAGINATION_LIMIT
from .spec.utils import docjoin


def rest(
    openapi: dict = None,
    setup_app: typing.Callable = None,
    base_path: str = None,
    commands: typing.List = None,
    allowed_tags: typing.Set = None,
    validate_docs: bool = False,
    servers: typing.List[str] = None,
    OpenApiSpecClass: typing.ClassVar = OpenApiSpec,
) -> OpenApiClient:
    """Create the OpenApi application server
    """
    return OpenApiClient(
        OpenApiSpecClass(
            OpenApi(**(openapi or {})),
            allowed_tags=allowed_tags,
            validate_docs=validate_docs,
            servers=servers
        ),
        base_path=base_path,
        commands=commands,
        setup_app=setup_app,
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


def orderable(*orderable_fields):
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


def searchable(*searchable_fields):
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
