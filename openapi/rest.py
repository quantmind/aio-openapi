from dataclasses import dataclass

from .spec import OpenApi
from .cli import OpenApiClient


def rest(setup_app=None, **kwargs):
    """Create the OpenApi application server
    """
    spec = OpenApi(**kwargs)
    return OpenApiClient(spec, setup_app=setup_app)


@dataclass
class Query:
    limit: int = 25
    offset: int = 0
