import pytest

from openapi.data.validate import validated_schema, ValidationErrors

from ..example.models import TaskAdd


def test_validated_schema():
    data = dict(
        title='test',
        severity=1
    )
    v = validated_schema(TaskAdd, data)
    assert len(data) == 2
    assert v


def test_validated_schema_errors():
    data = dict(
        severity=1
    )
    with pytest.raises(ValidationErrors) as e:
        validated_schema(TaskAdd, data)
    assert len(e.value.errors) == 1
