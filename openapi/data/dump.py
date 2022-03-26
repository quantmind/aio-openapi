from dataclasses import asdict, fields
from typing import Any, Dict, List, Optional, Union, cast

from openapi.types import Record

from ..utils import TypingInfo, iter_items
from .fields import DUMP


def is_nothing(value: Any) -> bool:
    if value == 0 or value is False:
        return False
    return not value


def dump(schema: Any, data: Any) -> Any:
    """Dump data with a given schema.

    :param schema: a valid :ref:`aio-openapi-schema`
    :param data: data to dump, if dataclasses are part of the schema,
        the `dump` metadata function will be used if available (see :func:`.data_field`)
    """
    type_info = cast(TypingInfo, TypingInfo.get(schema))
    if type_info.container is list:
        return dump_list(type_info.element, cast(List, data))
    elif type_info.container is dict:
        return dump_dict(type_info.element, cast(Dict, data))
    elif type_info.is_dataclass:
        return dump_dataclass(type_info.element, cast(Dict, data))
    else:
        return data


def dump_dataclass(schema: Any, data: Optional[Union[Dict, Record]] = None) -> Dict:
    """Dump a dictionary of data with a given dataclass dump functions
    If the data is not given, the schema object is assumed to be
    an instance of a dataclass.
    """
    if data is None:
        data = asdict(schema)
    elif isinstance(data, schema):
        data = asdict(data)
    cleaned = {}
    fields_ = {f.name: f for f in fields(schema)}
    for name, value in iter_items(data):
        if name not in fields_ or is_nothing(value):
            continue
        field = fields_[name]
        dump_value = field.metadata.get(DUMP)
        if dump_value:
            value = dump_value(value)
        cleaned[field.name] = dump(field.type, value)

    return cleaned


def dump_list(schema: Any, data: List) -> List[Dict]:
    """Validate a dictionary of data with a given dataclass"""
    return [dump(schema, d) for d in data]


def dump_dict(schema: Any, data: Dict[str, Any]) -> List[Dict]:
    """Validate a dictionary of data with a given dataclass"""
    return {name: dump(schema, d) for name, d in data.items()}
