from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

from ..data.view import DataView, Operation
from ..utils import TypingInfo


@dataclass
class op:
    """Decorator for a :class:`.ApiPath` view which specifies an operation object
    in an OpenAPI Path. Parameters are dataclasses used for validation and
    OpenAPI auto documentation.
    """

    body_schema: Any = None
    query_schema: Any = None
    response_schema: Any = None
    response: int = 200
    # responses: List[Any] = []

    def __call__(self, method) -> Callable:
        method.op = Operation(
            body_schema=TypingInfo.get(self.body_schema),
            query_schema=TypingInfo.get(self.query_schema),
            response_schema=TypingInfo.get(self.response_schema),
            response=self.response,
        )

        @wraps(method)
        async def _(view: DataView) -> Any:
            view.operation = method.op
            return await method(view)

        return _
