from dataclasses import dataclass
import typing

from .data.fields import Choice, IntegerValidator
from .cli import OpenApiClient
from .data.fields import data_field, bool_field
from .spec import OpenApi, OpenApiSpec
from .spec.utils import docjoin
from .spec.pagination import MAX_PAGINATION_LIMIT


def rest(
        openapi: dict=None,
        setup_app: object=None,
        base_path: str=None,
        commands: typing.List=None,
        allowed_tags: typing.Set=None,
        validate_docs: bool=False
):
    """Create the OpenApi application server
    """
    return OpenApiClient(
        OpenApiSpec(
            OpenApi(**(openapi or {})),
            allowed_tags=allowed_tags,
            validate_docs=validate_docs
        ),
        base_path=base_path,
        commands=commands,
        setup_app=setup_app
    )


@dataclass
class Query:
    limit: int = data_field(
        validator=IntegerValidator(min_value=1,
                                   max_value=MAX_PAGINATION_LIMIT),
        description='Limit the number of objects returned from the endpoint'
    )
    offset: int = data_field(
        validator=IntegerValidator(min_value=0),
        description=(
            'Number of objects to exclude. '
            'Use in conjunction with limit to paginate results'
        )
    )


def orderable(*orderable_fields):
    @dataclass
    class Orderable:
        order_by: str = data_field(
            validator=Choice(orderable_fields),
            description=(
                'Order results by given column (default ascending order). '
                f'Possible values are {docjoin(orderable_fields)}'
            )
        )
        order_desc: bool = bool_field(
            description=(
                'Change order direction to descending'
            )
        )
    return Orderable
