from typing import Dict

from .fields import DUMP
from ..utils import iter_items


def is_nothing(value):
    if value is 0 or value is False:
        return False
    return not value


def dump(schema: object, data: object) -> Dict:
    """Validate a dictionary of data with a given dataclass
    """
    cleaned = {}
    fields = schema.__dataclass_fields__
    for name, value in iter_items(data):
        if name not in fields or is_nothing(value):
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
