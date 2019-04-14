from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

import pytest

from openapi.data.fields import (
    VALIDATOR,
    BoolValidator,
    Choice,
    DateTimeValidator,
    DecimalValidator,
    EmailValidator,
    EnumValidator,
    IntegerValidator,
    ListValidator,
    NumberValidator,
    UUIDValidator,
    ValidationError,
    Validator,
    bool_field,
    data_field,
    date_time_field,
    decimal_field,
    email_field,
    enum_field,
    number_field,
    uuid_field,
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
        raise ValidationError(field, "invalid")


def test_base_validator():
    validator = Validator()
    field = data_field()
    with pytest.raises(ValidationError):
        validator(field, None)


def test_ListValidator_call_valid():
    value = "test"
    field = data_field()
    validator1 = FakeValidator()
    validator2 = FakeValidator()
    validator = ListValidator((validator1, validator2))
    assert validator(field, value) == "test"
    assert validator.dump(3) == "3"


def test_ListValidator_call_invalid():
    value = [1, "string"]
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
        validator(field, "id")


def test_UUIDValidator_dump():
    value = uuid4()
    validator = UUIDValidator()
    assert validator.dump(value) == value.hex
    assert validator.dump(value.hex) == value.hex


def test_EnumValidator_call_valid():
    field = enum_field(FakeEnum)
    validator = EnumValidator(FakeEnum)
    assert validator(field, "VALUE_A") == FakeEnum.VALUE_A.name


def test_EnumValidator_call_invalid():
    field = enum_field(FakeEnum)
    validator = EnumValidator(FakeEnum)
    with pytest.raises(ValidationError):
        validator(field, "VALUE_D")


def test_Choice_call_valid():
    field = data_field()
    validator = Choice(["a", "b", "c"])
    assert validator(field, "a") == "a"


def test_Choice_call_invalid():
    field = data_field()
    validator = Choice(["a", "b", "c"])
    with pytest.raises(ValidationError):
        validator(field, "d")


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
        validator(field, "invalid_date")


def test_DateTimeValidator_dump():
    value = datetime.now()
    validator = DateTimeValidator()
    assert validator.dump(value) == value.isoformat()
    assert validator.dump(value.isoformat()) == value.isoformat()


def test_DateTimeValidator_timezone():
    value = datetime.now()
    field = date_time_field(timezone=True)
    validator = field.metadata[VALIDATOR]
    with pytest.raises(ValidationError):
        validator(field, value)


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
        validator(field, "5")


def test_NumberValidator_dump():
    validator = NumberValidator(min_value=-10, max_value=10, precision=2)
    assert validator.dump(10) == 10
    assert validator.dump(-10) == -10
    assert validator.dump(5.55) == 5.55
    assert validator.dump(5.556) == 5.56


def test_IntegerValidator_valid():
    field = number_field()
    validator = IntegerValidator(min_value=-10, max_value=10)
    assert validator(field, 10) == 10
    assert validator(field, 0) == 0
    assert validator(field, -10) == -10
    assert validator(field, "-5") == -5


def test_IntegerValidator_invalid():
    field = number_field()
    validator = IntegerValidator(min_value=-10, max_value=10)
    with pytest.raises(ValidationError):
        validator(field, 11)
    with pytest.raises(ValidationError):
        validator(field, -11)
    with pytest.raises(ValidationError):
        validator(field, -1.12)


def test_IntegerValidator_dump():
    validator = IntegerValidator(min_value=-10, max_value=10)
    assert validator.dump(10) == 10
    assert validator.dump(0) == 0
    assert validator.dump(-10) == -10


def test_DecimalValidator_valid():
    field = decimal_field()
    validator = DecimalValidator(min_value=-10, max_value=10, precision=2)
    assert validator(field, 10) == 10
    assert validator(field, -10) == -10
    assert validator(field, 5.55) == Decimal("5.55")
    assert validator(field, 5.555) == Decimal("5.56")
    assert validator(field, "5.555") == Decimal("5.56")


def test_DecimalValidator_precision_None():
    field = decimal_field()
    validator = DecimalValidator(min_value=-10, max_value=10)
    assert validator(field, 10) == 10
    assert validator(field, -10) == -10
    assert validator(field, 5.555) == Decimal("5.555")
    assert validator(field, 5.555555555555555) == Decimal("5.555555555555555")


def test_DecimalValidator_invalid():
    field = decimal_field()
    validator = DecimalValidator(min_value=-10, max_value=10, precision=2)
    with pytest.raises(ValidationError):
        validator(field, "xy")
    with pytest.raises(ValidationError):
        validator(field, 11)
    with pytest.raises(ValidationError):
        validator(field, -11)


def test_DecimalValidator_dump():
    validator = DecimalValidator(min_value=-10, max_value=10, precision=2)
    assert validator.dump(Decimal(10)) == Decimal("10")
    assert validator.dump(Decimal(-10)) == Decimal("-10")
    assert validator.dump(Decimal("5.55")) == Decimal("5.55")
    assert validator.dump(Decimal("5.556")) == Decimal("5.56")


def test_email_validator_valid():
    field = email_field()
    assert EmailValidator()(field, "valid@email.com") == "valid@email.com"
    assert EmailValidator()(field, "a1-_@email.us") == "a1-_@email.us"
    assert EmailValidator()(field, "foo.top@kaputt.co") == "foo.top@kaputt.co"


def test_email_validator_invalid():
    field = email_field()
    with pytest.raises(ValidationError):
        EmailValidator()(field, "a@email")
    with pytest.raises(ValidationError):
        EmailValidator()(field, "email.com")
    with pytest.raises(ValidationError):
        EmailValidator()(field, "@email.com")
    with pytest.raises(ValidationError):
        EmailValidator()(field, 1)


def test_BoolValidator_valid():
    field = bool_field()
    validator = BoolValidator()
    assert validator(field, True) is True
    assert validator(field, False) is False
    assert validator(field, "TrUe") is True
    assert validator(field, "fAlSe") is False


def test_BoolValidator_invalid():
    field = bool_field()
    validator = BoolValidator()
    with pytest.raises(ValidationError):
        validator(field, None)
    with pytest.raises(ValidationError):
        validator(field, "f")
    with pytest.raises(ValidationError):
        validator(field, "t")


def test_BoolValidator_dump():
    validator = BoolValidator()
    assert validator.dump(True) is True
    assert validator.dump(False) is False
    assert validator.dump("TrUe") is True
    assert validator.dump("fAlSe") is False
