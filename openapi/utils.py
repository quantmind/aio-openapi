import os
import sys
import warnings
from dataclasses import is_dataclass
from inspect import isclass
from typing import Any, Dict, Hashable, Iterable, Iterator, List, NamedTuple, Optional

from .exc import InvalidTypeException

if sys.version_info >= (3, 7):
    from contextlib import asynccontextmanager  # noqa
else:  # pragma: no cover
    from ._py36 import asynccontextmanager  # noqa


py36_origins = {List: list, Dict: dict}
LOCAL = "local"
DEV = "dev"
PRODUCTION = "production"
NO_DEBUG = {"0", "false", "no"}
Null = object()


class TypingInfo(NamedTuple):
    element: type
    container: Optional[type] = None

    @property
    def is_dataclass(self) -> bool:
        return not self.container and is_dataclass(self.element)

    @property
    def typing(self) -> Any:
        if self.container is list:
            return List[_typing(self.element)]
        elif self.container is dict:
            return Dict[str, _typing(self.element)]
        else:
            return self.element

    @classmethod
    def get(cls, value: Any) -> Optional["TypingInfo"]:
        if value is None or isinstance(value, cls):
            return value
        origin = cls.get_origin(value)
        if not origin:
            if isinstance(value, list):
                warnings.warn(
                    "typing via lists is deprecated in version 1.5.* and "
                    "will be removed in version 1.6, use typing.List instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return TypingInfo(value[0], list)
            elif isclass(value):
                return cls(value)
            else:
                raise InvalidTypeException(
                    f"a class or typing annotation is required, got {value}"
                )
        elif origin is list:
            elem_info = cls.get(value.__args__[0])
            elem = elem_info if elem_info.container else elem_info.element
            return cls(elem, list)
        elif origin is dict:
            key, val = value.__args__
            if key is not str:
                raise InvalidTypeException(
                    f"Dict key annotation must be a string, got {key}"
                )

            elem_info = cls.get(val)
            elem = elem_info if elem_info.container else elem_info.element
            return cls(elem, dict)
        else:
            raise InvalidTypeException(
                f"Types or List and Dict typing is required, got {value}"
            )

    @classmethod
    def get_origin(cls, value: Any):
        origin = getattr(value, "__origin__", None)
        return py36_origins.get(origin, origin)


def get_env() -> str:
    return os.environ.get("PYTHON_ENV") or PRODUCTION


def get_debug_flag() -> bool:
    val = os.environ.get("DEBUG")
    if not val:
        return get_env() == LOCAL
    return val.lower() not in NO_DEBUG


def compact(**kwargs) -> Dict:
    return {k: v for k, v in kwargs.items() if v}


def compact_dict(kwargs: Dict) -> Dict:
    return {k: v for k, v in kwargs.items() if v is not None}


def replace_key(kwargs: Dict, from_key: Hashable, to_key: Hashable) -> Dict:
    value = kwargs.pop(from_key, Null)
    if value is not Null:
        kwargs[to_key] = value
    return kwargs


def iter_items(data: Iterable) -> Iterator:
    items = getattr(data, "items", None)
    if hasattr(items, "__call__"):
        return items()
    return iter(data)


def is_subclass(value: Any, Type: type) -> bool:
    origin = getattr(value, "__origin__", None) or value
    return isclass(origin) and issubclass(origin, Type)


def as_list(errors: Iterable) -> List[Dict[str, Any]]:
    return [
        {"field": field, "message": message} for field, message in iter_items(errors)
    ]


def error_dict(errors: List) -> Dict:
    return dict(((d["field"], d["message"]) for d in errors))


def _typing(element: Any) -> Any:
    return element.typing if isinstance(element, TypingInfo) else element
