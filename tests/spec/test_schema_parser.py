from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List
from unittest.mock import patch

import pytest

from openapi.data.fields import (
    as_field,
    bool_field,
    data_field,
    date_time_field,
    number_field,
)
from openapi.spec import SchemaParser
from openapi.spec.exceptions import InvalidSpecException, InvalidTypeException


def test_get_schema_ref():
    @dataclass
    class MyClass:
        str_field: str = data_field(description="String field")

    parser = SchemaParser()

    schema_ref = parser.get_schema_ref(MyClass)
    assert schema_ref == {"$ref": "#/components/schemas/MyClass"}
    assert "MyClass" in parser.group.parsed_schemas.keys()


def test_schema2json():
    @dataclass
    class OtherClass:
        str_field: str = data_field(description="String field")

    @dataclass
    class MyClass:
        """Test data
        """

        str_field: str = data_field(
            required=True, format="uuid", description="String field"
        )
        int_field: int = data_field(format="uint64", description="Int field")
        float_field: float = number_field(description="Float field")
        boolean_field: bool = bool_field(description="Bool field")
        map_field: Dict[str, int] = data_field(description="Dict field")
        free_field: Dict = data_field(description="Free field")
        datetime_field: datetime = date_time_field(description="Datetime field")
        ref_field: OtherClass = field(
            metadata={"required": True, "description": "Ref field"}, default=None
        )
        list_ref_field: List[OtherClass] = data_field(description="List field")

    parser = SchemaParser()
    schema_json = parser.schema2json(MyClass)
    expected = {
        "type": "object",
        "description": "Test data",
        "properties": {
            "str_field": {
                "type": "string",
                "format": "uuid",
                "description": "String field",
            },
            "int_field": {
                "type": "integer",
                "format": "uint64",
                "description": "Int field",
            },
            "float_field": {
                "type": "number",
                "format": "float",
                "description": "Float field",
            },
            "boolean_field": {"type": "boolean", "description": "Bool field"},
            "map_field": {
                "type": "object",
                "additionalProperties": {"type": "integer", "format": "int32"},
                "description": "Dict field",
            },
            "free_field": {"type": "object", "description": "Free field"},
            "datetime_field": {
                "type": "string",
                "format": "date-time",
                "description": "Datetime field",
            },
            "ref_field": {
                "$ref": "#/components/schemas/OtherClass",
                "description": "Ref field",
            },
            "list_ref_field": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/OtherClass"},
                "description": "List field",
            },
        },
        "required": ["str_field", "ref_field"],
        "additionalProperties": False,
    }
    assert schema_json == expected


def test_field2json():
    parser = SchemaParser([])
    str_json = parser.field2json(str)
    int_json = parser.field2json(int)
    float_json = parser.field2json(float)
    bool_json = parser.field2json(bool)
    datetime_json = parser.field2json(datetime)

    assert str_json == {"type": "string"}
    assert int_json == {"type": "integer", "format": "int32"}
    assert float_json == {"type": "number", "format": "float"}
    assert bool_json == {"type": "boolean"}
    assert datetime_json == {"type": "string", "format": "date-time"}


def test_field2json_format():
    parser = SchemaParser([])
    str_json = parser.field2json(as_field(str, format="uuid"))
    int_json = parser.field2json(as_field(int, format="int64"))

    assert str_json == {"type": "string", "format": "uuid"}
    assert int_json == {"type": "integer", "format": "int64"}


def test_field2json_invalid_type():
    class MyType:
        pass

    parser = SchemaParser([])
    with pytest.raises(InvalidTypeException):
        parser.field2json(MyType)


def test_field2json_missing_description():
    @dataclass
    class MyClass:
        desc_field: str = data_field(description="Valid field")
        no_desc_field: str = data_field()

    parser = SchemaParser(validate_docs=True)
    with pytest.raises(InvalidSpecException):
        parser.get_schema_ref(MyClass)


def test_enum2json():
    class MyEnum(Enum):
        FIELD_1 = 0
        FIELD_2 = 1
        FIELD_3 = 2

    parser = SchemaParser([])
    json_type = parser.field2json(MyEnum)
    assert json_type == {"type": "string", "enum": ["FIELD_1", "FIELD_2", "FIELD_3"]}


def test_list2json():
    @dataclass
    class MyClass:
        list_field: List[str]

    parser = SchemaParser([])
    with patch.object(parser, "field2json"):
        list_field = MyClass.__dataclass_fields__["list_field"]
        list_json = parser._list2json(list_field)

        assert list_json["type"] == "array"
        assert "items" in list_json.keys()
        assert list_json == {"type": "array", "items": parser.field2json.return_value}
        parser.field2json.assert_called_once_with(str, False)


def test_field2json_again():
    @dataclass
    class MyClass:
        str_field: str = field(
            metadata={"format": "uuid", "description": "String field"}
        )
        int_field: int = number_field(
            min_value=0, max_value=100, description="Int field"
        )

    parser = SchemaParser([])
    fields = MyClass.__dataclass_fields__
    str_json = parser.field2json(fields["str_field"])
    int_json = parser.field2json(fields["int_field"])

    assert str_json == {
        "type": "string",
        "format": "uuid",
        "description": "String field",
    }
    assert int_json == {
        "type": "integer",
        "format": "int32",
        "minimum": 0,
        "maximum": 100,
        "description": "Int field",
    }


def test_non_string_keys():
    @dataclass
    class MyClass:
        map_field: Dict[int, str] = data_field(description="Map field")

    parser = SchemaParser()
    with pytest.raises(InvalidTypeException):
        parser.schema2json(MyClass)
