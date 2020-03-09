from dataclasses import MISSING, Field, fields
from typing import Any, Dict, NamedTuple, Optional, Tuple, Union

from multidict import MultiDict

from ..utils import TypingInfo
from .fields import (
    ITEMS,
    POST_PROCESS,
    REQUIRED,
    VALIDATOR,
    ValidationError,
    as_field,
    field_ops,
)

NOT_VALID_TYPE = "not valid type"
OBJECT_EXPECTED = "expected an object"

ErrorType = Union[Dict, str, None]


class ValidatedData(NamedTuple):
    data: Any = None
    errors: ErrorType = None


class ValidationErrors(ValueError):
    def __init__(self, errors) -> None:
        self.errors = errors


def validated_schema(schema: Any, data: Any, *, strict: bool = True) -> Any:
    """Validate data with a given schema and return a valid representation of the data
    as a schema instance

    :param schema: a valid  :ref:`aio-openapi-schema` or a :class:`.TypingInfo` object
    :param data: a data object to validate against the schema
    :param strict: if `True` validation is strict, i.e. missing required parameters
        will cause validation to fails
    """
    return validate(schema, data, strict=strict, raise_on_errors=True, as_schema=True)


def validate(
    schema: Any,
    data: Any,
    *,
    strict: bool = True,
    multiple: bool = False,
    raise_on_errors: bool = False,
    items: Optional[Field] = None,
    as_schema: bool = False,
) -> Any:
    """Validate data with a given schema

    :param schema: a typing annotation or a :class:`.TypingInfo` object
    :param data: a data object to validate against the schema
    :param strict: if `True` validation is strict, i.e. missing required parameters
        will cause validation to fails
    :param multiple: allow parameters to have multiple values
    :param raise_on_errors: when `True` failure of validation will result in a
        `ValidationErrors` error, otherwise a :class:`.ValidatedData` object
        is returned.
    :param items: an optional Field for items in a composite type (`List` or `Dict`)
    :param as_schema: return the schema object rather than simple data type
        (dataclass rather than dict for example)
    """
    type_info = TypingInfo.get(schema)
    try:
        if type_info.container is list:
            vdata = validate_list(
                type_info.element,
                data,
                strict=strict,
                multiple=multiple,
                items=items,
                as_schema=as_schema,
            )
        elif type_info.container is dict:
            vdata = validate_dict(
                type_info.element,
                data,
                strict=strict,
                multiple=multiple,
                items=items,
                as_schema=as_schema,
            )
        elif type_info.is_dataclass:
            vdata = validate_dataclass(
                type_info.element,
                data,
                strict=strict,
                multiple=multiple,
                as_schema=as_schema,
            )
        elif type_info.is_union:
            vdata = validate_union(type_info.element, data, as_schema=as_schema)
        elif type_info.element is Any:
            vdata = data
        else:
            vdata = validate_simple(type_info.element, data)
    except ValidationErrors as e:
        if not raise_on_errors:
            return ValidatedData(errors=e.errors)
        raise
    else:
        return vdata if raise_on_errors else ValidatedData(data=vdata, errors={})


def validate_simple(schema: type, data: Any) -> Any:
    if isinstance(data, schema):
        return data
    raise ValidationErrors(NOT_VALID_TYPE)


def validate_union(
    schema: Tuple[TypingInfo, ...], data: Any, as_schema: bool = False, **kw,
) -> Any:
    for type_info in schema:
        try:
            return validate(type_info, data, raise_on_errors=True, as_schema=as_schema)
        except ValidationErrors:
            continue
    raise ValidationErrors(NOT_VALID_TYPE)


def validate_list(
    schema: type,
    data: list,
    *,
    strict: bool = True,
    multiple: bool = False,
    as_schema: bool = False,
    items: Optional[Field] = None,
) -> ValidatedData:
    validated = []
    if isinstance(data, (list, tuple)):
        items = as_field(schema, field=items)
        for d in data:
            v = collect_value(
                items, d, strict=strict, multiple=multiple, as_schema=as_schema,
            )
            validated.append(v)
        return validated
    else:
        raise ValidationErrors("expected a sequence")


def validate_dict(
    schema: type,
    data: Dict[str, Any],
    *,
    strict: bool = True,
    multiple: bool = False,
    as_schema: bool = False,
    items: Optional[Field] = None,
) -> ValidatedData:
    if isinstance(data, dict):
        validated = ValidatedData(data={}, errors={})
        items = as_field(schema, field=items)
        for name, d in data.items():
            try:
                validated.data[name] = collect_value(
                    items, d, strict=strict, multiple=multiple, as_schema=as_schema,
                )
            except ValidationErrors as exc:
                validated.errors[name] = exc.errors
        if validated.errors:
            raise ValidationErrors(validated.errors)
        return validated.data
    else:
        raise ValidationErrors(OBJECT_EXPECTED)


def validate_dataclass(
    schema: type,
    data: Union[Dict[str, Any], MultiDict],
    *,
    strict: bool = True,
    multiple: bool = False,
    as_schema: bool = False,
    **kw,
) -> ValidatedData:
    errors: Dict = {}
    cleaned: Dict = {}
    try:
        data = MultiDict(data)
    except TypeError:
        raise ValidationErrors(OBJECT_EXPECTED)
    for field in fields(schema):
        try:
            required = field.metadata.get(REQUIRED, True)
            default = get_default(field)
            if strict and default is not None and data.get(field.name) is None:
                data[field.name] = default

            if field.name not in data and required and strict:
                raise ValidationError(field.name, "required")

            for name in field_ops(field):
                if name not in data:
                    continue

                if multiple:
                    values = data.getall(name)
                    if len(values) > 1:
                        collected = []
                        for v in values:
                            v = collect_value(field, v)
                            if v is not None:
                                collected.append(v)
                        value = collected if collected else None
                    else:
                        value = collect_value(field, values[0], as_schema=as_schema)
                else:
                    value = collect_value(field, data[name], as_schema=as_schema)

                cleaned[name] = value

        except ValidationError as exc:
            errors[exc.field] = exc.message
        except ValidationErrors as exc:
            errors[name] = exc.errors

    if not errors:
        validate = getattr(schema, "validate", None)
        if validate:
            validate(cleaned, errors)

    if errors:
        raise ValidationErrors(errors)
    return schema(**cleaned) if as_schema else cleaned


def collect_value(field: Field, value: Any, **kw) -> Any:
    if is_null(value):
        return None

    validator = field.metadata.get(VALIDATOR)
    if validator:
        value = validator(field, value)

    kw.update(raise_on_errors=True, items=field.metadata.get(ITEMS))
    value = validate(field.type, value, **kw)

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
