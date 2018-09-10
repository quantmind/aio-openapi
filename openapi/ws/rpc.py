from functools import wraps
from typing import Any
from dataclasses import dataclass

from ..data.validate import validate, ValidationErrors


@dataclass
class ws_rpc:
    """Defines a Websocket RPC method in an OpenAPI Path
    """
    body_schema: Any = None
    response_schema: Any = None

    def __call__(self, method):
        method.ws_rpc = self

        @wraps(method)
        async def _(view, payload):
            if self.body_schema:
                d = validate(self.body_schema, payload)
                if d.errors:
                    raise ValidationErrors(d.errors)
                payload = d.data
            data = await method(view, payload)
            return view.dump(self.response_schema, data)

        return _
