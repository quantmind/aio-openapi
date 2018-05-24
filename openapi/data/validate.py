from typing import Dict
from dataclasses import dataclass

from .fields import VALIDATOR, REQUIRED, DEFAULT, ValidationError


@dataclass
class ValidatedData:
    data: Dict
    errors: Dict


def validate(schema, data):
    """Validate a dictionary of data with a given dataclass
    """
    errors = {}
    cleaned = {}
    for field in schema.__dataclass_fields__.values():
        try:
            required = field.metadata.get(REQUIRED)
            if field.name not in data and DEFAULT not in field.metadata:
                if required:
                    raise ValidationError(field.name, 'required')
                continue

            validator = field.metadata.get(VALIDATOR)
            default = field.metadata.get(DEFAULT)
            value = data.get(field.name, default)

            if validator:
                value = validator(field, value, data)

            if value and not isinstance(value, field.type):
                try:
                    value = field.type(value)
                except (TypeError, ValueError):
                    raise ValidationError(field.name, 'not a valid value')

            cleaned[field.name] = value

        except ValidationError as exc:
            errors[exc.field] = exc.message

    if not errors:
        validate = getattr(schema, 'validate', None)
        if validate:
            validate(cleaned, errors)

    return ValidatedData(data=cleaned, errors=errors)
