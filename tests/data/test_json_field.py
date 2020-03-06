from dataclasses import dataclass, fields
from typing import Dict, List

import pytest

from openapi.data.fields import VALIDATOR, JSONValidator, json_field, ValidationError
from openapi.data.validate import ValidationErrors, validated_schema


@dataclass
class TJson:
    a: List = json_field()
    b: Dict = json_field()


def test_validator():
    dfields = fields(TJson)
    assert isinstance(dfields[0].metadata[VALIDATOR], JSONValidator)
    with pytest.raises(ValidationErrors):
        validated_schema(TJson, dict(a="{]}", b="{}"))


def test_validattionb_fail_list():
    with pytest.raises(ValidationErrors):
        validated_schema(TJson, dict(a="{}", b="{}"))
    s = validated_schema(TJson, dict(a="[]", b="{}"))
    assert s.a == []
    assert s.b == {}


def test_validattionb_fail_dict():
    with pytest.raises(ValidationErrors):
        validated_schema(TJson, dict(a="[]", b="[]"))


def test_json_field_error():
    field = json_field()
    validator = field.metadata[VALIDATOR]
    with pytest.raises(ValidationError):
        validator(field, object())
