from typing import Dict

from .fields import DUMP
from ..utils import iter_items

NOTHING = frozenset(('', None))


def dump(schema: object, data: object) -> Dict:
    """Validate a dictionary of data with a given dataclass
    """
    cleaned = {}
    fields = schema.__dataclass_fields__
    for name, value in iter_items(data):
        if name not in fields or value in NOTHING:
            continue
        field = fields[name]
        dump = field.metadata.get(DUMP)
        if dump:
            value = dump(value)
        cleaned[field.name] = value

    return cleaned


def dump_list(schema, data):
    """Validate a dictionary of data with a given dataclass
    """
    return [dump(schema, d) for d in data]
