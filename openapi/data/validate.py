from dataclasses import MISSING, Field, dataclass, fields
from typing import Any, Dict, List, Tuple, Union, cast

from multidict import MultiDict

from ..utils import TypingInfo, is_subclass
from .fields import POST_PROCESS, REQUIRED, VALIDATOR, ValidationError, field_ops


@dataclass
class ValidatedData:
    data: Any
    errors: Dict


class ValidationErrors(ValueError):
    def __init__(self, errors) -> None:
        self.errors = errors


def validated_schema(schema, data, *, strict: bool = True):
    d = validate(schema, data, strict=strict)
    if d.errors:
        raise ValidationErrors(d.errors)
    return schema(**d.data)


def validate(
    schema: Any,
    data: Union[Dict[str, Any], MultiDict],
    *,
    strict: bool = True,
    multiple: bool = False,
) -> ValidatedData:
    """Validate a dictionary of data with a given dataclass
    """
    type_info = TypingInfo.get(schema)
    if type_info.container is list:
        return validate_list(type_info.element, data, strict=strict, multiple=multiple)
    elif type_info.container is dict:
        return validate_dict(type_info.element, data, strict=strict, multiple=multiple)
    elif type_info.is_dataclass:
        return validate_dataclass(
            type_info.element, data, strict=strict, multiple=multiple
        )
    else:
        return ValidatedData(data=data, errors={})


def validate_list(
    schema: type, data: list, *, strict: bool = True, multiple: bool = False,
) -> ValidatedData:
    validated = ValidatedData(data=[], errors={})
    if isinstance(data, list):
        for d in data:
            v = validate(schema, d, strict=strict, multiple=multiple)
            validated.data.append(v.data)
            validated.errors.update(v.errors)
    else:
        validated.errors["message"] = "expected a sequence"
    return validated


def validate_dict(
    schema: type, data: Dict[str, Any], *, strict: bool = True, multiple: bool = False,
) -> ValidatedData:
    validated = ValidatedData(data={}, errors={})
    for name, d in data.items():
        v = validate(schema, d, strict=strict, multiple=multiple)
        validated.data[name] = v.data
        validated.errors.update(v.errors)
    return validated


def validate_dataclass(
    schema: type,
    data: Union[Dict[str, Any], MultiDict],
    *,
    strict: bool = True,
    multiple: bool = False,
) -> ValidatedData:
    errors: Dict = {}
    cleaned: Dict = {}
    data = MultiDict(data)
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

                if multiple:
                    values = cast(MultiDict, data).getall(name)
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


def collect_value(field: Field, name: str, value: Any) -> Any:
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


def is_null(value: Any) -> bool:
    return value is None or value == "NULL"


def get_default(field: Field) -> Any:
    if field.default_factory is not MISSING:
        value = field.default_factory()
    else:
        value = field.default
    return value if value is not MISSING else None
