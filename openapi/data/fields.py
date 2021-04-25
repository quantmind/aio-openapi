from dataclasses import Field, dataclass, field, fields
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from numbers import Number
from typing import Any, Callable, Dict, Iterator, Optional, Tuple
from uuid import UUID

from dateutil.parser import parse as parse_date
from email_validator import EmailNotValidError, validate_email

from .. import json, tz
from ..utils import compact_dict, str2bool

REQUIRED = "required"
VALIDATOR = "OPENAPI_VALIDATOR"
DESCRIPTION = "description"
POST_PROCESS = "post_process"
DUMP = "dump"
FORMAT = "format"
OPS = "ops"
ITEMS = "items"

DataClass = Any


PRIMITIVE_TYPES: Dict[Any, Dict] = {
    str: {"type": "string"},
    bytes: {"type": "string", FORMAT: "binary"},
    int: {"type": "integer", FORMAT: "int32"},
    float: {"type": "number", FORMAT: "float"},
    bool: {"type": "boolean"},
    date: {"type": "string", FORMAT: "date"},
    datetime: {"type": "string", FORMAT: "date-time"},
    Decimal: {"type": "number"},
}


class ValidationError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message


def field_dict(dc: type) -> Dict[str, Field]:
    return {f.name: f for f in fields(dc)}


def data_field(
    required: bool = False,
    validator: Optional[Callable[[Field, Any], Any]] = None,
    dump: Optional[Callable[[Any], Any]] = None,
    format: str = None,
    description: str = None,
    items: Optional[Field] = None,
    post_process: Callable[[Any], Any] = None,
    ops: Tuple = (),
    meta: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Field:
    """Extend a dataclass field with the following metadata

    :param validator: optional callable which accept field and raw value
        as inputs and return the validated value
    :param required: boolean specifying if field is required
    :param dump: optional callable which receive the field value and convert to
        the desired value to serve in requests
    :param format: optional string which represents the JSON schema format
    :param description: optional field description
    :param items: field for items of the current field
        (only used for `List` and `Dict` fields)
    :param post_process: post processor function executed after validation
    :param ops: optional tuple of strings specifying available operations
    :param meta: optional dictionary with additional metadata
    """
    if isinstance(validator, Validator) and not dump:
        dump = validator.dump
    if "default_factory" not in kwargs:
        kwargs.setdefault("default", None)
    meta = meta or {}

    f = field(
        metadata=compact_dict(
            {
                VALIDATOR: validator,
                REQUIRED: required,
                DUMP: dump,
                DESCRIPTION: description,
                ITEMS: items,
                POST_PROCESS: post_process,
                FORMAT: format,
                OPS: ops,
                **meta,
            }
        ),
        **kwargs,
    )
    return f


def str_field(min_length: int = 0, max_length: int = 0, **kw) -> Field:
    """A specialized :func:`.data_field` for strings

    :param min_length: minim length of string
    :param max_length: maximum length of string
    """
    kw.setdefault(
        "validator", StrValidator(min_length=min_length, max_length=max_length)
    )
    return data_field(**kw)


def bool_field(**kw) -> Field:
    """Specialized :func:`.data_field` for bool types"""
    kw.setdefault("validator", BoolValidator())
    return data_field(**kw)


def uuid_field(format: str = "uuid", **kw) -> Field:
    """A UUID field with validation"""
    kw.setdefault("validator", UUIDValidator())
    return data_field(format=format, **kw)


def number_field(
    min_value: Optional[Number] = None,
    max_value: Optional[Number] = None,
    precision: Optional[int] = None,
    **kw,
) -> Field:
    """A specialized :func:`.data_field` for numeric values

    :param min_value: minimum value
    :param max_value: maximum value
    :param precision: decimal precision
    """
    kw.setdefault("validator", NumberValidator(min_value, max_value, precision))
    return data_field(**kw)


def integer_field(
    min_value: Optional[Number] = None,
    max_value: Optional[Number] = None,
    **kw,
) -> Field:
    """A specialized :func:`.data_field` for integer values

    :param min_value: minimum value
    :param max_value: maximum value
    """
    kw.setdefault("validator", IntegerValidator(min_value, max_value))
    return data_field(**kw)


def decimal_field(min_value=None, max_value=None, precision=None, **kw) -> Field:
    kw.setdefault("validator", DecimalValidator(min_value, max_value, precision))
    return data_field(**kw)


def email_field(min_length: int = 0, max_length: int = 0, **kw) -> Field:
    """A specialized :func:`.data_field` for emails, validation via the
    `email_validator` third party library

    :param min_length: minimum length of email
    :param max_length: maximum length of email
    """
    kw.setdefault(
        "validator", EmailValidator(min_length=min_length, max_length=max_length)
    )
    return data_field(**kw)


def enum_field(EnumClass, **kw) -> Field:
    """A specialized :func:`.data_field` for enums

    :param EnumClass: enum for validation
    """
    kw.setdefault("validator", EnumValidator(EnumClass))
    return data_field(**kw)


def date_field(**kw) -> Field:
    """A specialized :func:`.data_field` for dates"""
    kw.setdefault("validator", DateValidator())
    return data_field(**kw)


def date_time_field(timezone=False, **kw) -> Field:
    """A specialized :func:`.data_field` for datetimes

    :param timezone: timezone for validation
    """
    kw.setdefault("validator", DateTimeValidator(timezone=timezone))
    return data_field(**kw)


def as_field(item: Any, *, field: Optional[Field] = None, **kw) -> Field:
    if isinstance(item, Field):
        return item
    field = field or data_field(**kw)
    if field.type and field.type is not item:
        raise RuntimeError("Cannot override field type")
    field.type = item
    return field


def json_field(**kw) -> Field:
    """A specialized :func:`.data_field` for JSON data"""
    kw.setdefault("validator", JSONValidator())
    return data_field(**kw)


# Utilities


def field_ops(field: Field) -> Iterator[str]:
    yield field.name
    for op in field.metadata.get(OPS, ()):
        yield f"{field.name}:{op}"


# VALIDATORS


class Validator:
    def __call__(self, field: Field, value: Any) -> Any:
        raise ValidationError(field.name, "invalid")

    def openapi(self, prop: Dict) -> None:
        pass

    def dump(self, value: Any) -> Any:
        return value


@dataclass
class StrValidator(Validator):
    min_length: int = 0
    max_length: int = 0

    def __call__(self, field: Field, value: Any) -> Any:
        if not isinstance(value, str):
            raise ValidationError(field.name, "Must be a string")
        if self.min_length and len(value) < self.min_length:
            raise ValidationError(field.name, "Too short")
        if self.max_length and len(value) > self.max_length:
            raise ValidationError(field.name, "Too long")
        return value

    def openapi(self, prop: Dict) -> None:
        if self.min_length:
            prop["minLength"] = self.min_length
        if self.max_length:
            prop["maxLength"] = self.max_length


@dataclass
class EmailValidator(StrValidator):
    def __call__(self, field: Field, value: Any) -> Any:
        value = super().__call__(field, value)
        try:
            validate_email(value, check_deliverability=False)
        except EmailNotValidError:
            raise ValidationError(field.name, "%s not a valid email" % value) from None
        return value


class ListValidator(Validator):
    def __init__(self, validators) -> None:
        self.validators = validators

    def __call__(self, field: Field, value: Any) -> Any:
        for validator in self.validators:
            value = validator(field, value)
        return value

    def dump(self, value: Any) -> Any:
        for validator in self.validators:
            dump = getattr(validator, "dump", None)
            if hasattr(dump, "__call__"):
                value = dump(value)
        return value

    def openapi(self, prop: Dict) -> None:
        for validator in self.validators:
            if isinstance(validator, Validator):
                validator.openapi(prop)


class UUIDValidator(Validator):
    def __call__(self, field: Field, value: Any) -> Any:
        try:
            if not isinstance(value, UUID):
                value = UUID(str(value))
            return value.hex
        except ValueError:
            raise ValidationError(field.name, "%s not a valid uuid" % value)

    def dump(self, value: Any) -> Any:
        if isinstance(value, UUID):
            return value.hex
        return value


class EnumValidator(Validator):
    """Enum validator to and from name (str) and value (int)"""

    def __init__(self, EnumClass) -> None:
        self.EnumClass = EnumClass

    def __call__(self, field: Field, value: Any) -> Any:
        try:
            e = value
            if isinstance(e, str):
                e = getattr(self.EnumClass, value)
            if isinstance(e, self.EnumClass):
                return e if field.type == self.EnumClass else e.name
            raise AttributeError
        except AttributeError:
            raise ValidationError(field.name, "%s not valid" % value)

    def dump(self, value: Any) -> Any:
        if isinstance(value, self.EnumClass):
            return value.name
        return value


class Choice(Validator):
    def __init__(self, choices) -> None:
        self.choices = choices

    def __call__(self, field: Field, value: Any) -> Any:
        if value not in self.choices:
            raise ValidationError(field.name, "%s not valid" % value)
        return value

    def openapi(self, prop: Dict) -> None:
        prop["enum"] = sorted(self.choices)


class DateValidator(Validator):
    def dump(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.date().isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        return value

    def __call__(self, field: Field, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = parse_date(value).date()
            except ValueError:
                pass
        if not isinstance(value, date):
            raise ValidationError(field.name, "%s not valid format" % value)
        return value


class DateTimeValidator(Validator):
    def __init__(self, timezone=False) -> None:
        self.timezone = timezone

    def dump(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def __call__(self, field: Field, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = parse_date(value)
            except ValueError:
                pass
        if not isinstance(value, datetime):
            raise ValidationError(field.name, "%s not valid format" % value)
        if self.timezone and not value.tzinfo:
            if value.time() == time():
                value = tz.as_utc(value)
            else:
                raise ValidationError(field.name, "Timezone information required")
        return value


NumericErrors = (TypeError, ValueError, InvalidOperation)


class BoundedNumberValidator(Validator):
    def __init__(
        self, min_value: Optional[Number] = None, max_value: Optional[Number] = None
    ) -> None:
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, field: Field, value: Any) -> Any:
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                field.name, "%s less than %s" % (value, self.min_value)
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                field.name, "%s greater than %s" % (value, self.max_value)
            )
        return value

    def dump(self, value: Any) -> Number:
        return self.to_number(value)

    def openapi(self, prop: Dict) -> None:
        if self.min_value is not None:
            prop["minimum"] = self.min_value
        if self.max_value is not None:
            prop["maximum"] = self.max_value

    def to_number(self, value: Any) -> Number:
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return Decimal(value)
        else:
            return value


class NumberValidator(BoundedNumberValidator):
    def __init__(
        self,
        min_value: Optional[Number] = None,
        max_value: Optional[Number] = None,
        precision: Optional[int] = None,
    ) -> None:
        super().__init__(min_value=min_value, max_value=max_value)
        self.precision = precision

    def __call__(self, field: Field, value: Any) -> Any:
        try:
            value = self.to_number(value)
            if self.precision is not None:
                value = round(value, self.precision)
        except NumericErrors:
            raise ValidationError(field.name, "%s not valid number" % value)
        return super().__call__(field, value)

    def dump(self, value: Any) -> Any:
        value = self.to_number(value)
        if self.precision is not None:
            return round(value, self.precision)
        return value


class IntegerValidator(BoundedNumberValidator):
    def __call__(self, field: Field, value: Any) -> Any:
        try:
            value = self.to_number(value)
            if not isinstance(value, int):
                raise ValueError
        except NumericErrors:
            raise ValidationError(field.name, "%s not valid integer" % value)
        return super().__call__(field, value)


class DecimalValidator(NumberValidator):
    def __call__(self, field: Field, value: Any) -> Any:
        try:
            value = self.to_number(value)
            if not isinstance(value, Decimal):
                value = Decimal(str(value))
        except NumericErrors:
            raise ValidationError(field.name, "%s not valid Decimal" % value)
        return super().__call__(field, value)


class BoolValidator(Validator):
    def __call__(self, field: Field, value: Any) -> bool:
        return str2bool(value)

    def dump(self, value: Any) -> bool:
        return str2bool(value)


class JSONValidator(Validator):
    def __call__(self, field: Field, value: Any) -> Any:
        try:
            return self.dump(value)
        except (json.JSONDecodeError, TypeError):
            raise ValidationError(field.name, "%s not valid" % value)

    def dump(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        return json.loads(json.dumps(value))
