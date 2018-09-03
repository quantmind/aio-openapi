import os
import logging
from functools import wraps
from inspect import isclass
from collections import Mapping
from typing import List, Dict


LOCAL = 'local'
DEV = 'dev'
PRODUCTION = 'production'
NO_DEBUG = {'0', 'false', 'no'}
Null = object()


class _AsyncGeneratorContextManager:    # pragma: no cover
    def __init__(self, func, args, kwds):
        self.gen = func(*args, **kwds)
        self.func, self.args, self.kwds = func, args, kwds
        doc = getattr(func, "__doc__", None)
        if doc is None:
            doc = type(self).__doc__
        self.__doc__ = doc

    async def __aenter__(self):
        try:
            return await self.gen.__anext__()
        except StopAsyncIteration:
            raise RuntimeError("generator didn't yield") from None

    async def __aexit__(self, typ, value, traceback):
        if typ is None:
            try:
                await self.gen.__anext__()
            except StopAsyncIteration:
                return
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                value = typ()
            try:
                await self.gen.athrow(typ, value, traceback)
                raise RuntimeError("generator didn't stop after throw()")
            except StopAsyncIteration as exc:
                return exc is not value
            except RuntimeError as exc:
                if exc is value:
                    return False
                if isinstance(value, (StopIteration, StopAsyncIteration)):
                    if exc.__cause__ is value:
                        return False
                raise
            except BaseException as exc:
                if exc is not value:
                    raise


def get_env() -> str:
    return os.environ.get('PYTHON_ENV') or PRODUCTION


def get_debug_flag() -> str:
    val = os.environ.get('DEBUG')
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
    items = getattr(data, 'items', None)
    if hasattr(items, '__call__'):
        return items()
    return iter(data)


def getLogger():
    level = (os.environ.get('LOG_LEVEL') or 'info').upper()
    if level != 'NONE':
        name = os.environ.get('APP_NAME') or 'openapi'
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            logger.setLevel(getattr(logging, level))
            logger.addHandler(logging.StreamHandler())
        return logger


def is_subclass(value, Klass):
    return isclass(value) and issubclass(value, Klass)


def as_list(errors: Dict) -> List:
    return [
        {'field': field, 'message': message} for
        field, message in iter_items(errors)
    ]


def error_dict(errors: List) -> Dict:
    return dict(((d['field'], d['message']) for d in errors))


def asynccontextmanager(func):
    @wraps(func)
    def helper(*args, **kwds):
        return _AsyncGeneratorContextManager(func, args, kwds)
    return helper
