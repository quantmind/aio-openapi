import pytest
from datetime import datetime
from enum import Enum
from uuid import uuid4

from openapi.data.fields import (
    ValidationError, data_field, bool_field, uuid_field, number_field,
    decimal_field, email_field, enum_field, date_time_field,  ListValidator,
    UUIDValidator, EnumValidator, Choice, DateTimeValidator, NumberValidator,
    DecimalValidator, email_validator, BoolValidator, Validator
)


class FakeEnum(Enum):
    VALUE_A = 1
    VALUE_B = 2
    VALUE_C = 3


class FakeValidator(Validator):
    def dump(self, value):
        return str(value)

    def __call__(self, field, value, data=None):
        return value


class FakeValidatorError(Validator):
    def __call__(self, field, value, data=None):
        raise ValidationError(field, 'invalid')


def test_ListValidator_call_valid():
    value = [1, 'string']
    field = data_field()
    validator1 = FakeValidator()
    validator2 = FakeValidator()
    validator = ListValidator((validator1, validator2))
    assert validator(field, value) == [1, 'string']


def test_ListValidator_call_invalid():
    value = [1, 'string']
    field = data_field()
    validator1 = FakeValidator()
    validator2 = FakeValidatorError()
    validator = ListValidator((validator1, validator2))
    with pytest.raises(ValidationError):
        validator(field, value)


def test_UUIDValidator_call_valid():
    uuid = uuid4()
    field = uuid_field()
    validator = UUIDValidator()
    assert validator(field, uuid) == uuid.hex
    assert validator(field, uuid.hex) == uuid.hex


def test_UUIDValidator_call_invalid():
    field = uuid_field()
    validator = UUIDValidator()
    with pytest.raises(ValidationError):
        validator(field, 'id')


def test_UUIDValidator_dump():
    value = uuid4()
    validator = UUIDValidator()
    assert validator.dump(value) == value.hex
    assert validator.dump(value.hex) == value.hex


def test_EnumValidator_call_valid():
    field = enum_field(FakeEnum)
    validator = EnumValidator(FakeEnum)
    assert validator(field, 'VALUE_A') == 'VALUE_A'


def test_EnumValidator_call_invalid():
    field = enum_field(FakeEnum)
    validator = EnumValidator(FakeEnum)
    with pytest.raises(ValidationError):
        validator(field, 'VALUE_D')


def test_Choice_call_valid():
    field = data_field()
    validator = Choice(['a', 'b', 'c'])
    assert validator(field, 'a') == 'a'


def test_Choice_call_invalid():
    field = data_field()
    validator = Choice(['a', 'b', 'c'])
    with pytest.raises(ValidationError):
        validator(field, 'd')


def test_DateTimeValidator_call_valid():
    value = datetime.now()
    field = date_time_field()
    validator = DateTimeValidator()
    assert validator(field, value) == value
    assert validator(field, value.isoformat()) == value


def test_DateTimeValidator_call_invalid():
    field = date_time_field()
    validator = DateTimeValidator()
    with pytest.raises(ValidationError):
        validator(field, 'invalid_date')


def test_DateTimeValidator_dump():
    value = datetime.now()
    validator = DateTimeValidator()
    assert validator.dump(value) == value.isoformat()
    assert validator.dump(value.isoformat()) == value.isoformat()


def test_NumberValidator_valid():
    field = number_field()
    validator = NumberValidator(min_value=-10, max_value=10, precision=2)
    assert validator(field, 10) == 10
    assert validator(field, -10) == -10
    assert validator(field, 5.55) == 5.55
    assert validator(field, 5.555) == 5.55


def test_NumberValidator_invalid():
    field = number_field()
    validator = NumberValidator(min_value=-10, max_value=10, precision=2)
    with pytest.raises(ValidationError):
        validator(field, 11)
    with pytest.raises(ValidationError):
        validator(field, -11)
    with pytest.raises(ValidationError):
        validator(field, '5')


def test_NumberValidator_dump():
    validator = NumberValidator(min_value=-10, max_value=10, precision=2)
    assert validator.dump(10) == 10
    assert validator.dump(-10) == -10
    assert validator.dump(5.55) == 5.55
    assert validator.dump(5.556) == 5.56


def test_DecimalValidator_valid():
    field = decimal_field()
    validator = DecimalValidator(min_value=-10, max_value=10, precision=2)
    assert validator(field, 10) == 10
    assert validator(field, -10) == -10
    # assert validator(field, 5.55) == 5.55
    # assert validator(field, 5.555) == Decimal(5.55)
    # assert validator(field, '5.555') == Decimal(5.55)
    # assert validator(field, (5, 555)) == Decimal(5.55)


def test_DecimalValidator_invalid():
    field = decimal_field()
    validator = DecimalValidator(min_value=-10, max_value=10, precision=2)
    with pytest.raises(ValidationError):
        validator(field, 11)
    with pytest.raises(ValidationError):
        validator(field, -11)


def test_DecimalValidator_dump():
    validator = DecimalValidator(min_value=-10, max_value=10, precision=2)
    assert validator.dump(10) == 10
    assert validator.dump(-10) == -10
    assert validator.dump(5.55) == 5.55
    assert validator.dump(5.556) == 5.56


def test_email_validator_valid():
    field = email_field()
    assert email_validator(field, 'valid@email.com') == 'valid@email.com'
    assert email_validator(field, 'a1-_@email.us') == 'a1-_@email.us'
    assert email_validator(field, 'a@a.a') == 'a@a.a'


def test_email_validator_invalid():
    field = email_field()
    with pytest.raises(ValidationError):
        email_validator(field, 'a@email.comm')
    with pytest.raises(ValidationError):
        email_validator(field, '#$%@email.com')
    with pytest.raises(ValidationError):
        email_validator(field, 'email.com')
    with pytest.raises(ValidationError):
        email_validator(field, '@email.com')
    with pytest.raises(ValidationError):
        email_validator(field, 1)


def test_BoolValidator_valid():
    field = bool_field()
    validator = BoolValidator()
    assert validator(field, True) is True
    assert validator(field, False) is False
    assert validator(field, 'TrUe') is True
    assert validator(field, 'fAlSe') is False


def test_BoolValidator_invalid():
    field = bool_field()
    validator = BoolValidator()
    with pytest.raises(ValidationError):
        validator(field, None)
    with pytest.raises(ValidationError):
        validator(field, 'f')
    with pytest.raises(ValidationError):
        validator(field, 't')


def test_BoolValidator_dump():
    validator = BoolValidator()
    assert validator.dump(True) is True
    assert validator.dump(False) is False
    assert validator.dump('TrUe') is True
    assert validator.dump('fAlSe') is False
