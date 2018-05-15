import os


DEV = 'dev'
PRODUCTION = 'production'
NO_DEBUG = {'0', 'false', 'no'}


def get_env():
    return os.environ.get('OPENAPI_DEBUG') or PRODUCTION


def get_debug_flag():
    val = os.environ.get('OPENAPI_DEBUG')
    if not val:
        return get_env() == DEV
    return val.lower() not in NO_DEBUG


def compact(**kwargs):
    return {k: v for k, v in kwargs.items() if v}


def compact_dict(kwargs):
    return {k: v for k, v in kwargs.items() if v}


def iter_items(data):
    items = getattr(data, 'items', None)
    if hasattr(items, '__call__'):
        return items()
    return iter(data)
