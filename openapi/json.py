from functools import partial

import simplejson

loads = partial(simplejson.loads, use_decimal=True)
dumps = partial(simplejson.dumps, use_decimal=True)

__all__ = ['loads', 'dumps']
