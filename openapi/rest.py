from dataclasses import dataclass

from .spec import OpenApi
from .cli import OpenApiClient
from .data.fields import data_field, NumberValidator
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
        validator=NumberValidator(min_value=1, max_value=MAX_PAGINATION_LIMIT),
        description='Limit the number of objects returned from the endpoint'
    )
    offset: int = data_field(
        validator=NumberValidator(min_value=0),
        description=(
            'Number of objects to exclude. '
            'Use in conjunction with limit to paginate results'
        )
    )
