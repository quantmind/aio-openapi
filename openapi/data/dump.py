from dataclasses import asdict, fields
from typing import Any, Dict, List, Optional

from ..utils import iter_items
from .fields import DUMP


def is_nothing(value: Any) -> bool:
    if value == 0 or value is False:
        return False
    return not value


def dump(schema: type, data: Optional[Dict] = None) -> Dict:
    """Dump a dictionary of data with a given dataclass dump functions
    If the data is not given, the schema object is assumed to be
    an instance of a dataclass.
    """
    data = asdict(schema) if data is None else data
    cleaned = {}
    fields_ = {f.name: f for f in fields(schema)}
    for name, value in iter_items(data):
        if name not in fields_ or is_nothing(value):
            continue
        field = fields_[name]
        dump = field.metadata.get(DUMP)
        if dump:
            value = dump(value)
        cleaned[field.name] = value

    return cleaned


def dump_list(schema: type, data: List[Dict]) -> List[Dict]:
    """Validate a dictionary of data with a given dataclass
    """
    return [dump(schema, d) for d in data]
