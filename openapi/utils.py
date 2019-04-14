import os
import sys
from collections.abc import Mapping
from inspect import isclass
from typing import Dict, List

if sys.version_info >= (3, 7):
    from contextlib import asynccontextmanager  # noqa
else:
    from ._py36 import asynccontextmanager  # noqa


LOCAL = "local"
DEV = "dev"
PRODUCTION = "production"
NO_DEBUG = {"0", "false", "no"}
Null = object()


def get_env() -> str:
    return os.environ.get("PYTHON_ENV") or PRODUCTION


def get_debug_flag() -> str:
    val = os.environ.get("DEBUG")
    if not val:
        return get_env() == LOCAL
    return val.lower() not in NO_DEBUG


def compact(**kwargs) -> Dict:
    return {k: v for k, v in kwargs.items() if v}


def compact_dict(kwargs) -> Dict:
    return {k: v for k, v in kwargs.items() if v is not None}


def replace_key(kwargs, from_key, to_key):
    value = kwargs.pop(from_key, Null)
    if value is not Null:
        kwargs[to_key] = value
    return kwargs


def mapping_copy(data):
    if isinstance(data, Mapping):
        return data.copy()
    return dict(data)


def iter_items(data):
    items = getattr(data, "items", None)
    if hasattr(items, "__call__"):
        return items()
    return iter(data)


def is_subclass(value, Type):
    origin = getattr(value, "__origin__", None) or value
    return isclass(origin) and issubclass(origin, Type)


def as_class(value):
    return value if isclass(value) else type(value)


def as_list(errors: Dict) -> List:
    return [
        {"field": field, "message": message} for field, message in iter_items(errors)
    ]


def error_dict(errors: List) -> Dict:
    return dict(((d["field"], d["message"]) for d in errors))
