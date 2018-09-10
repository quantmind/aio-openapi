from typing import Dict, List, Tuple
from dataclasses import dataclass

from .fields import VALIDATOR, REQUIRED, DEFAULT, ValidationError, field_ops
from ..utils import mapping_copy


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


def validate(schema, data, *, strict=True, multiple=False):
    """Validate a dictionary of data with a given dataclass
    """
    errors = {}
    cleaned = {}
    data = mapping_copy(data)
    for field in schema.__dataclass_fields__.values():
        try:
            required = field.metadata.get(REQUIRED)
            if strict and DEFAULT in field.metadata:
                data.setdefault(field.name, field.metadata[DEFAULT])

            if field.name not in data and required and strict:
                raise ValidationError(field.name, 'required')

            for name in field_ops(field):
                if name not in data:
                    continue

                if multiple and hasattr(data, 'getall'):
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
        validate = getattr(schema, 'validate', None)
        if validate:
            validate(cleaned, errors)

    return ValidatedData(data=cleaned, errors=errors)


def collect_value(field, name, value):
    if value is None or value == 'NULL':
        return None

    validator = field.metadata.get(VALIDATOR)
    if validator:
        value = validator(field, value)

    Type = getattr(field.type, '_gorg', None)
    if Type in (List, Tuple):
        # hack - we need to formalize this and allow for nested validators
        if not isinstance(value, (list, tuple)):
            raise ValidationError(name, 'not a valid value')
        value = list(value)
    else:
        types = getattr(field.type, '__args__', None) or (field.type,)
        types = tuple((getattr(t, '__origin__', None) or t) for t in types)
        if not isinstance(value, types):
            try:
                value = field.type(value)
            except (TypeError, ValueError):
                raise ValidationError(name, 'not a valid value')

    return value
