from dataclasses import dataclass
from functools import wraps
from typing import Any


@dataclass
class op:
    """Defines an operation object in an OpenAPI Path
    """

    body_schema: Any = None
    query_schema: Any = None
    response_schema: Any = None
    response: int = 200
    # responses: List[Any] = []

    def __call__(self, method):
        method.op = self

        @wraps(method)
        async def _(view):
            view.request["operation"] = self
            return await method(view)

        return _
