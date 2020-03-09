from dataclasses import asdict, dataclass
from typing import Dict, List, Union

import pytest

from openapi.data import fields
from openapi.data.validate import ValidationErrors, validate, validated_schema
from tests.example.models import Foo, Moon, Permission, Role, TaskAdd


@dataclass
class Foo2:
    text: str = fields.str_field(min_length=3, description="Just some text")
    param: Union[str, int] = fields.integer_field(
        description="String accepted but convert to int"
    )
    done: bool = fields.bool_field(description="Is Foo done?")


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
    validator = fields.ListValidator([fields.NumberValidator(-1, 1)])
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
    assert isinstance(d.permissions[0], Permission)


def test_post_process():
    d = validate(Moon, {})
    assert d.data == {}
    d = validate(Moon, {"names": "luca, max"})
    assert d.data == {"names": ["luca", "max"]}


def test_validate_list():
    data = [dict(paths=["bla"], methods=["get"], body=dict(a="test"))]
    d = validate(List[Permission], data)
    assert not d.errors
    assert isinstance(d.data, list)


def test_validate_union():
    schema = Union[int, str]
    d = validate(schema, "3")
    assert d.data == "3"
    d = validate(schema, 3)
    assert d.data == 3
    d = validate(schema, 3.3)
    assert d.errors


def test_validate_union_nested():
    schema = Union[int, str, Dict[str, Union[int, str]]]
    d = validate(schema, "3")
    assert d.data == "3"
    d = validate(schema, 3)
    assert d.data == 3
    d = validate(schema, dict(foo=3, bla="ciao"))
    assert d.data == dict(foo=3, bla="ciao")


def test_foo():
    assert validate(Foo, {}).errors
    assert validate(Foo, dict(text="ciao")).errors
    assert validate(Foo, dict(text="ciao"), strict=False).data == dict(text="ciao")
    valid = dict(text="ciao", param=3)
    assert validate(Foo, valid).data == dict(text="ciao", param=3, done=False)
    d = validated_schema(List[Foo], [valid])
    assert len(d) == 1
    assert isinstance(d[0], Foo)


def test_foo2():
    s = validated_schema(Foo2, dict(text="ciao", param="3", done="no"))
    assert s.done is False
