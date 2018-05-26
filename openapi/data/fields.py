import re
from decimal import Decimal
from uuid import uuid4, UUID
from datetime import datetime
from dataclasses import field

from dateutil.parser import parse as parse_date

from ..utils import compact_dict

email_pattern = re.compile("^[a-zA-Z0-9-_]+@[a-zA-Z0-9]+\.[a-z]{1,3}$")


DEFAULT = 'default'
REQUIRED = 'required'
VALIDATOR = 'OPENAPI_VALIDATOR'
DUMP = 'dump',
FORMAT = 'format'


class ValidationError(ValueError):

    def __init__(self, field, message):
        self.field = field
        self.message = message


def data_field(
        required=False, validator=None, default=None, dump=None, format=None):
    """Extend a dataclass field with

    :param validator: optional callable which accept (field, value, data)
                      as inputs and return the validated value
    :param required: boolean specifying if field is required
    :param default: optional callable returning the default value
                    if value is missing
    :param dump: optional callable which receive the field value and convert to
                 the desired value to serve in requests
    :param format: optional string which represents the JSON schema format
    """
    if isinstance(validator, Validator) and not dump:
        dump = validator.dump

    f = field(metadata=compact_dict({
        VALIDATOR: validator,
        REQUIRED: required,
        DEFAULT: default,
        DUMP: dump,
        FORMAT: format
    }))
    return f


def bool_field(**kwargs):
    if 'validator' not in kwargs:
        kwargs['validator'] = lambda f, v, d: str(v).lower() == 'true'
    return data_field(**kwargs)


def uuid_field(required=False):
    """A UUID field with validation
    """
    return data_field(
        required=required,
        validator=UUIDValidator(),
        default=uuid4,
        format='uuid'
    )


def number_field(required=False, min_value=None,
                 max_value=None, precision=None):
    return data_field(
        required=required,
        validator=NumberValidator(min_value, max_value, precision)
    )


def decimal_field(required=False, min_value=None,
                  max_value=None, precision=None):
    return data_field(
        required=required,
        validator=DecimalValidator(min_value, max_value, precision)
    )


def email_field(required=False):
    return data_field(required=required, validator=email_validator)


def enum_field(EnumClass, **kwargs):
    kwargs['validator'] = EnumValidator(EnumClass)
    return data_field(**kwargs)


def date_time_field(required=False):
    return data_field(required=required, validator=DateTimeValidator())


# VALIDATORS


def email_validator(field, value, data):
    value = str(value)
    if not email_pattern.match(value):
        raise ValidationError(field.name, '%s not a valid email' % value)
    return value


class Validator:
    dump = None

    def __call__(self, field, value, data):
        raise ValidationError(field.name, 'inavlid')


class ListValidator(Validator):

    def __init__(self, validators):
        self.validators = validators

    def __call__(self, field, value, data):
        for validator in self.validators:
            value = validator(field, value, data)
        return value

    def dump(self, value):
        for validator in self.validators:
            dump = getattr(validator, 'dump', None)
            if hasattr(dump, '__call__'):
                value = dump(value)
        return dump


class UUIDValidator(Validator):

    def __call__(self, field, value, data):
        try:
            if not isinstance(value, UUID):
                value = UUID(str(value))
            return value.hex
        except ValueError:
            raise ValidationError(field.name, '%s not a valid uuid' % value)

    def dump(self, value):
        if isinstance(value, UUID):
            return value.hex
        return value


class EnumValidator(Validator):
    """Enum validator to and from name (str) and value (int)"""

    def __init__(self, EnumClass):
        self.EnumClass = EnumClass

    def __call__(self, field, value, data):
        if value is None:
            return
        try:
            e = getattr(self.EnumClass, value)
            if isinstance(e, self.EnumClass):
                return e.name
            raise AttributeError
        except AttributeError:
            raise ValidationError(field.name, '%s not valid' % value)


class Choice(Validator):

    def __init__(self, choices):
        self.choices = choices

    def __call__(self, field, value, data):
        if value not in self.choices:
            raise ValidationError(field.name, '%s not valid' % value)
        return value


class DateTimeValidator(Validator):

    def dump(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def __call__(self, field, value, data):
        if isinstance(value, str):
            try:
                value = parse_date(value)
            except ValueError:
                pass
        if not isinstance(value, datetime):
            raise ValidationError(
                field.name, '%s not valid format' % value
            )
        return value


class NumberValidator(Validator):

    def __init__(self, min_value=None, max_value=None, precision=None):
        self.min_value = min_value
        self.max_value = max_value
        self.precision = precision if precision is not None else 10

    def __call__(self, field, value, data):
        try:
            value = round(value, self.precision)
        except (ValueError, TypeError):
            raise ValidationError(field.name, '%s not valid number' % value)
        if self.min_value is not None and value <= self.min_value:
            raise ValidationError(field.name, '%s less than %s'
                                  % (value, self.min_value))
        if self.max_value is not None and value >= self.max_value:
            raise ValidationError(field.name, '%s greater than %s'
                                  % (value, self.max_value))
        return value

    def dump(self, value):
        return round(value, self.precision)


class DecimalValidator(NumberValidator):
    def __call__(self, field, value, precision):
        try:
            value = Decimal(value)
        except TypeError:
            raise ValidationError(field.name, '%s not valid Decimal' % value)
        return super().__call__(field, value, precision)
