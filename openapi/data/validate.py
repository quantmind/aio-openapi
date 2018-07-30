from typing import Dict
from dataclasses import dataclass

from .fields import VALIDATOR, REQUIRED, DEFAULT, ValidationError, field_ops


@dataclass
class ValidatedData:
    data: Dict
    errors: Dict


class ValidationErrors(ValueError):

    def __init__(self, errors):
        self.errors = errors


def validated_schema(schema, data, strict=True):
    d = validate(schema, data, strict)
    if d.errors:
        raise ValidationErrors(d.errors)
    return schema(**d.data)


def validate(schema, data, strict=True):
    """Validate a dictionary of data with a given dataclass
    """
    data = dict(data)
    errors = {}
    cleaned = {}
    for field in schema.__dataclass_fields__.values():
        try:
            required = field.metadata.get(REQUIRED)
            validator = field.metadata.get(VALIDATOR)
            if DEFAULT in field.metadata:
                data.setdefault(field.name, field.metadata[DEFAULT])

            if field.name not in data and required and strict:
                raise ValidationError(field.name, 'required')

            for name in field_ops(field):
                if name not in data:
                    continue
                value = data[name]

                if value is None or value == 'NULL':
                    cleaned[name] = None
                    continue

                if validator:
                    value = validator(field, value)

                if not isinstance(
                        value,
                        getattr(field.type, '__origin__', field.type)
                ):
                    try:
                        value = field.type(value)
                    except (TypeError, ValueError):
                        raise ValidationError(name, 'not a valid value')

                cleaned[name] = value

        except ValidationError as exc:
            errors[exc.field] = exc.message

    if not errors:
        validate = getattr(schema, 'validate', None)
        if validate:
            validate(cleaned, errors)

    return ValidatedData(data=cleaned, errors=errors)
