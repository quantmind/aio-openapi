from openapi.db import CrudDB

from .db import meta
from .db_additional import additional_meta

db = CrudDB("", additional_meta(meta()))
