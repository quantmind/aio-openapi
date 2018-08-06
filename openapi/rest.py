from dataclasses import dataclass

from .data.fields import Choice, IntegerValidator
from .cli import OpenApiClient
from .data.fields import data_field, bool_field
from .spec import OpenApi
from .spec.pagination import MAX_PAGINATION_LIMIT


def rest(setup_app=None, base_path=None, commands=None, **kwargs):
    """Create the OpenApi application server
    """
    spec = OpenApi(**kwargs)
    return OpenApiClient(
        spec, base_path=base_path, commands=commands, setup_app=setup_app
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
                'Order results by given column (default ascending order)'
            )
        )
        order_desc: bool = bool_field(
            description=(
                'Change order direction to descending'
            )
        )
    return Orderable
