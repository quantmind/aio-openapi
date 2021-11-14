import os
from dataclasses import is_dataclass
from inspect import isclass
from typing import (
    Any,
    Dict,
    Hashable,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    TypeVar,
    Union,
    cast,
)

from .exc import InvalidTypeException
from .types import Record


def get_origin(value: Any) -> Any:
    return getattr(value, "__origin__", None)


LOCAL = "local"
DEV = "dev"
PRODUCTION = "production"
NO_DEBUG = {"0", "false", "no"}
Null = object()
#
# this should be Union[type, "TypingInfo"] but recursive types are not supported in mypy
ElementType = Any


def get_args(value, defaults):
    return getattr(value, "__args__", None) or defaults


KT, VT = get_args(Dict, (TypeVar("KT"), TypeVar("VT")))
(T,) = get_args(List, (TypeVar("T"),))


class TypingInfo(NamedTuple):
    """Information about a type annotation"""

    element: ElementType
    container: Optional[type] = None

    @property
    def is_dataclass(self) -> bool:
        """True if :attr:`.element` is a dataclass"""
        return not self.container and is_dataclass(self.element)

    @property
    def is_union(self) -> bool:
        """True if :attr:`.element` is a union of typing info"""
        return isinstance(self.element, tuple)

    @property
    def is_complex(self) -> bool:
        """True if :attr:`.element` is either a dataclass or a union"""
        return self.container is not None or self.is_union

    @classmethod
    def get(cls, value: Any) -> Optional["TypingInfo"]:
        """Create a :class:`.TypingInfo` from a typing annotation or
        another typing info

        :param value: typing annotation
        """
        if value is None or isinstance(value, cls):
            return value
        origin = get_origin(value)
        if not origin:
            if value is Any or isclass(value):
                return cls(value)
            else:
                raise InvalidTypeException(
                    f"a class or typing annotation is required, got {value}"
                )
        elif origin is list:
            (val,) = get_args(value, (T,))
            if val is T:
                val = Any
            elem_info = cast(TypingInfo, cls.get(val))
            elem = elem_info if elem_info.is_complex else elem_info.element
            return cls(elem, list)
        elif origin is dict:
            key, val = get_args(value, (KT, VT))
            if key is KT:
                key = str
            if val is VT:
                val = Any
            if key is not str:
                raise InvalidTypeException(
                    f"Dict key annotation must be a string, got {key}"
                )

            elem_info = cast(TypingInfo, cls.get(val))
            elem = elem_info if elem_info.is_complex else elem_info.element
            return cls(elem, dict)
        elif origin is Union:
            elem = tuple(cls.get(val) for val in value.__args__)
            return cls(elem)
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
    if isinstance(data, Record):
        data = data._asdict()
    if isinstance(data, Mapping):
        return data.items()
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


TRUE_VALUES = frozenset(("yes", "true", "t", "1"))


def str2bool(v: Union[str, bool, int]):
    return str(v).lower() in TRUE_VALUES
