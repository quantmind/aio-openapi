from dataclasses import MISSING, dataclass, fields
from typing import Dict, List, Tuple

from ..utils import is_subclass, mapping_copy
from .fields import REQUIRED, VALIDATOR, POST_PROCESS, ValidationError, field_ops


@dataclass
class ValidatedData:
    data: Dict
    errors: Dict


class ValidationErrors(ValueError):
    def __init__(self, errors):
        self.errors = errors


def validated_schema(schema, data, *, strict=True):
    d = validate(schema, data, strict=strict)
    if d.errors:
        raise ValidationErrors(d.errors)
    return schema(**d.data)


def validate(schema, data: Dict, *, strict: bool = True, multiple: bool = False):
    """Validate a dictionary of data with a given dataclass
    """
    errors = {}
    cleaned = {}
    data = mapping_copy(data)
    for field in fields(schema):
        try:
            required = field.metadata.get(REQUIRED)
            default = get_default(field)
            if strict and default is not None and data.get(field.name) is None:
                data[field.name] = default

            if field.name not in data and required and strict:
                raise ValidationError(field.name, "required")

            for name in field_ops(field):
                if name not in data:
                    continue

                if multiple and hasattr(data, "getall"):
                    values = data.getall(name)
                    if len(values) > 1:
                        collected = []
                        for v in values:
                            v = collect_value(field, name, v)
                            if v is not None:
                                collected.append(v)
                        value = collected if collected else None
                    else:
                        value = collect_value(field, name, values[0])
                else:
                    value = collect_value(field, name, data[name])

                cleaned[name] = value

        except ValidationError as exc:
            errors[exc.field] = exc.message

    if not errors:
        validate = getattr(schema, "validate", None)
        if validate:
            validate(cleaned, errors)

    return ValidatedData(data=cleaned, errors=errors)


def collect_value(field, name, value):
    if is_null(value):
        return None

    validator = field.metadata.get(VALIDATOR)
    if validator:
        value = validator(field, value)

    if is_subclass(field.type, List) or is_subclass(field.type, Tuple):
        # hack - we need to formalize this and allow for nested validators
        if not isinstance(value, (list, tuple)):
            raise ValidationError(name, "not a valid value")
        value = list(value)
    elif is_subclass(field.type, Dict):
        if not isinstance(value, dict):
            raise ValidationError(name, "not a valid value")
    else:
        types = getattr(field.type, "__args__", None) or (field.type,)
        types = tuple((getattr(t, "__origin__", None) or t) for t in types)
        if not isinstance(value, types):
            try:
                value = field.type(value)
            except (TypeError, ValueError):
                raise ValidationError(name, "not a valid value")

    post_process = field.metadata.get(POST_PROCESS)
    return post_process(value) if post_process else value


def is_null(value):
    return value is None or value == "NULL"


def get_default(field):
    if field.default_factory is not MISSING:
        value = field.default_factory()
    else:
        value = field.default
    return value if value is not MISSING else None
