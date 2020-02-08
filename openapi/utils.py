import os
import sys
import warnings
from dataclasses import is_dataclass
from inspect import isclass
from typing import (
    Any,
    Dict,
    Hashable,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    TypeVar,
    cast,
)

from .exc import InvalidTypeException

if sys.version_info >= (3, 7):
    from contextlib import asynccontextmanager  # noqa

    def get_origin(value: Any) -> Any:
        return getattr(value, "__origin__", None)


else:  # pragma: no cover
    from ._py36 import asynccontextmanager  # noqa

    py36_origins = {List: list, Dict: dict}

    def get_origin(value: Any) -> Any:
        try:
            if value in py36_origins:
                origin = value
            else:
                origin = getattr(value, "__origin__", None)
        except TypeError:
            origin = getattr(value, "__origin__", None)
        return py36_origins.get(origin, origin)


LOCAL = "local"
DEV = "dev"
PRODUCTION = "production"
NO_DEBUG = {"0", "false", "no"}
Null = object()
#
# this should be Union[type, "TypingInfo"] but recursive types are not supported in mypy
ElementType = Any


KT, VT = Dict.__args__ or (TypeVar("KT"), TypeVar("VT"))
(T,) = List.__args__ or (TypeVar("T"),)


class TypingInfo(NamedTuple):
    element: ElementType
    container: Optional[type] = None

    @property
    def is_dataclass(self) -> bool:
        return not self.container and is_dataclass(self.element)

    @classmethod
    def get(cls, value: Any) -> Optional["TypingInfo"]:
        if value is None or isinstance(value, cls):
            return value
        origin = get_origin(value)
        if not origin:
            if isinstance(value, list):
                warnings.warn(
                    "typing via lists is deprecated in version 1.5.* and "
                    "will be removed in version 1.6, use typing.List instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return cls(value[0], list)
            elif isclass(value):
                return cls(value)
            else:
                raise InvalidTypeException(
                    f"a class or typing annotation is required, got {value}"
                )
        elif origin is list:
            (val,) = value.__args__ or (T,)
            if val is T:
                val = str
            elem_info = cast(TypingInfo, cls.get(val))
            elem = elem_info if elem_info.container else elem_info.element
            return cls(elem, list)
        elif origin is dict:
            key, val = value.__args__ or (KT, VT)
            if key is KT:
                key = str
            if val is VT:
                val = str
            if key is not str:
                raise InvalidTypeException(
                    f"Dict key annotation must be a string, got {key}"
                )

            elem_info = cast(TypingInfo, cls.get(val))
            elem = elem_info if elem_info.container else elem_info.element
            return cls(elem, dict)
        else:
            raise InvalidTypeException(
                f"Types or List and Dict typing is required, got {value}"
            )


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
