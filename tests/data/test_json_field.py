from dataclasses import dataclass
from typing import Dict, List

import pytest

from openapi.data import fields
from openapi.data.validate import ValidationErrors, validated_schema


@dataclass
class TJson:
    a: List = fields.json_field()
    b: Dict = fields.json_field()


def test_validator():
    dfields = TJson.__dataclass_fields__
    assert isinstance(dfields["a"].metadata[fields.VALIDATOR], fields.JSONValidator)
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
