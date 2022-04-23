from typing import Callable, Dict, List, Optional, Sequence

from aiohttp.web import Application

from .cli import OpenApiClient
from .spec import OpenApi, OpenApiSpec, Redoc


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
