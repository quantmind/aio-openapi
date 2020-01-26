from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional

from ..utils import TypingInfo


@dataclass
class op:
    """Defines an operation object in an OpenAPI Path
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
        async def _(view):
            view.request["operation"] = method.op
            return await method(view)

        return _


@dataclass
class Operation:
    body_schema: Optional[TypingInfo] = None
    query_schema: Optional[TypingInfo] = None
    response_schema: Optional[TypingInfo] = None
    response: int = 200
