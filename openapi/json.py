from datetime import datetime
from functools import partial
from uuid import UUID

import simplejson


def encoder(obj):
    if isinstance(obj, UUID):
        return int(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError


loads = partial(simplejson.loads, use_decimal=True)
dumps = partial(simplejson.dumps, use_decimal=True, default=encoder)

__all__ = ['loads', 'dumps']
