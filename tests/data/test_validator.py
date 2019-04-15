from dataclasses import asdict

import pytest

from openapi.data.fields import ListValidator, NumberValidator
from openapi.data.validate import ValidationErrors, validate, validated_schema

from ..example.models import Moon, Permission, Role, TaskAdd


def test_validated_schema():
    data = dict(title="test", severity=1, unique_title="test")
    v = validated_schema(TaskAdd, data)
    assert len(data) == 3
    assert len(asdict(v)) == 5


def test_validated_schema_errors():
    data = dict(severity=1)
    with pytest.raises(ValidationErrors) as e:
        validated_schema(TaskAdd, data)
    assert len(e.value.errors) == 1


def test_openapi_listvalidator():
    validator = ListValidator([NumberValidator(-1, 1)])
    props = {}
    validator.openapi(props)
    assert props["minimum"] == -1
    assert props["maximum"] == 1


def test_permission():
    data = dict(paths=["bla"], methods=["get"], body=dict(a="test"))
    d = validated_schema(Permission, data)
    assert d.action == "allow"
    assert d.paths == ["bla"]
    assert d.body == dict(a="test")


def test_role():
    data = dict(
        name="test",
        permissions=[dict(paths=["bla"], methods=["get"], body=dict(a="test"))],
    )
    d = validated_schema(Role, data)
    assert isinstance(d.permissions[0], dict)


def test_post_process():
    d = validate(Moon, {})
    assert d.data == {}
    d = validate(Moon, {"names": "luca, max"})
    assert d.data == {"names": ["luca", "max"]}
