from dataclasses import asdict

import pytest

from openapi.data.validate import validated_schema, ValidationErrors
from openapi.data.fields import ListValidator, NumberValidator

from ..example.models import TaskAdd


def test_validated_schema():
    data = dict(
        title='test',
        severity=1,
        unique_title='test'
    )
    v = validated_schema(TaskAdd, data)
    assert len(data) == 3
    assert len(asdict(v)) == 5


def test_validated_schema_errors():
    data = dict(
        severity=1
    )
    with pytest.raises(ValidationErrors) as e:
        validated_schema(TaskAdd, data)
    assert len(e.value.errors) == 1


def test_openapi_listvalidator():
    validator = ListValidator([NumberValidator(-1, 1)])
    props = {}
    validator.openapi(props)
    assert props['minimum'] == -1
    assert props['maximum'] == 1
