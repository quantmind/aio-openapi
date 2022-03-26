from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import pytest

from openapi.data.fields import (
    as_field,
    bool_field,
    data_field,
    date_time_field,
    number_field,
)
from openapi.exc import InvalidSpecException, InvalidTypeException
from openapi.spec import SchemaParser


@pytest.fixture
def parser() -> SchemaParser:
    return SchemaParser()


def test_get_schema_ref(parser: SchemaParser):
    @dataclass
    class MyClass:
        str_field: str = data_field(description="String field")

    schema_ref = parser.get_schema_info(MyClass)
    assert schema_ref == {"$ref": "#/components/schemas/MyClass"}
    assert "MyClass" in parser.schemas_to_parse


def test_schema2json(parser: SchemaParser):
    @dataclass
    class OtherClass:
        str_field: str = data_field(description="String field")

    @dataclass
    class MyClass:
        """Test data"""

        raw: str
        str_field: str = data_field(
            required=True, format="uuid", description="String field"
        )
        int_field: int = data_field(format="uint64", description="Int field")
        float_field: float = number_field(description="Float field")
        boolean_field: bool = bool_field(description="Bool field")
        map_field: Dict[str, int] = data_field(description="Dict field")
        free_field: Dict[str, str] = data_field(description="Free field")
        datetime_field: datetime = date_time_field(description="Datetime field")
        ref_field: OtherClass = field(
            metadata={"required": True, "description": "Ref field"}, default=None
        )
        list_ref_field: List[OtherClass] = data_field(description="List field")
        random: Optional[str] = None

    schema_json = parser.schema2json(MyClass)
    expected = {
        "type": "object",
        "description": "Test data",
        "properties": {
            "raw": {
                "type": "string",
            },
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
            "free_field": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Free field",
            },
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
            "random": {"type": "string"},
        },
        "required": ["raw", "str_field", "ref_field"],
        "additionalProperties": False,
    }
    assert schema_json == expected


@pytest.mark.parametrize(
    "field,schema",
    (
        (str, {"type": "string"}),
        (int, {"type": "integer", "format": "int32"}),
        (float, {"type": "number", "format": "float"}),
        (bool, {"type": "boolean"}),
        (datetime, {"type": "string", "format": "date-time"}),
        (Optional[str], {"type": "string", "required": False}),
    ),
)
def test_field2json(parser, field, schema):
    assert parser.field2json(field) == schema


def test_field2json_format():
    parser = SchemaParser([])
    str_json = parser.field2json(as_field(str, format="uuid"))
    int_json = parser.field2json(as_field(int, format="int64"))

    assert str_json == {"type": "string", "format": "uuid"}
    assert int_json == {"type": "integer", "format": "int64"}


def test_field2json_invalid_type():
    class MyType:
        pass

    parser = SchemaParser()
    with pytest.raises(InvalidTypeException):
        parser.field2json(MyType)


def test_field2json_missing_description():
    @dataclass
    class MyClass:
        desc_field: str = data_field(description="Valid field")
        no_desc_field: str = data_field()

    parser = SchemaParser(validate_docs=True)
    with pytest.raises(InvalidSpecException):
        parser.schema2json(MyClass)


def test_enum2json():
    class MyEnum(Enum):
        FIELD_1 = 0
        FIELD_2 = 1
        FIELD_3 = 2

    parser = SchemaParser([])
    json_type = parser.field2json(MyEnum)
    assert json_type == {"type": "string", "enum": ["FIELD_1", "FIELD_2", "FIELD_3"]}


def test_list2json() -> None:
    @dataclass
    class MyClass:
        list_field: List[str]

    parser = SchemaParser()
    info = parser.get_schema_info(MyClass)
    assert info == {"$ref": "#/components/schemas/MyClass"}
    assert len(parser.schemas_to_parse) == 1
    parsed = parser.parsed_schemas()
    myclass = parsed["MyClass"]
    list_json = myclass["properties"]["list_field"]
    assert list_json["type"] == "array"
    assert list_json["items"] == {"type": "string"}


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
