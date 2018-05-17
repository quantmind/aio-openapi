import pytest
from unittest.mock import patch
from typing import List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from openapi.spec import SchemaParser
from openapi.spec.exceptions import InvalidTypeException


def test_get_schema_ref():
    @dataclass
    class MyClass:
        str_field: str

    parser = SchemaParser([MyClass])

    schema_ref = parser._get_schema_ref(MyClass)
    assert schema_ref == {'$ref': '#/components/schemas/MyClass'}
    assert 'MyClass' in parser.parsed_schemas.keys()


def test_schema2json():
    @dataclass
    class OtherClass:
        str_field: str

    @dataclass
    class MyClass:
        str_field: str = field(metadata={'required': True, 'format': 'uuid'})
        int_field: int = field(metadata={'format': 'uint64'})
        float_field: float
        bool_field: bool
        datetime_field: datetime
        ref_field: OtherClass = field(metadata={'required': True})
        list_ref_field: List[OtherClass]

    parser = SchemaParser([])
    schema_json = parser._schema2json(MyClass)
    expected = {
        'type': 'object',
        'properties': {
            'str_field': {
                'type': 'string',
                'format': 'uuid'
            }, 'int_field': {
                'type': 'integer',
                'format': 'uint64'
            }, 'float_field': {
                'type': 'number',
                'format': 'float'
            }, 'bool_field': {
                'type': 'boolean'
            }, 'datetime_field': {
                'type': 'string',
                'format': 'date-time'
            }, 'ref_field': {
                '$ref': '#/components/schemas/OtherClass'
            }, 'list_ref_field': {
                'type': 'array',
                'items': {
                    '$ref': '#/components/schemas/OtherClass'
                }
            }
        },
        'required': ['str_field', 'ref_field'],
        'additionalProperties': False
    }
    assert schema_json == expected


def test_type2json():
    parser = SchemaParser([])
    str_json = parser._type2json(str)
    int_json = parser._type2json(int)
    float_json = parser._type2json(float)
    bool_json = parser._type2json(bool)
    datetime_json = parser._type2json(datetime)

    assert str_json == {'type': 'string'}
    assert int_json == {'type': 'integer', 'format': 'int32'}
    assert float_json == {'type': 'number', 'format': 'float'}
    assert bool_json == {'type': 'boolean'}
    assert datetime_json == {'type': 'string', 'format': 'date-time'}


def test_type2json_format():
    parser = SchemaParser([])
    str_json = parser._type2json(str, field_format='uuid')
    int_json = parser._type2json(int, field_format='int64')

    assert str_json == {'type': 'string', 'format': 'uuid'}
    assert int_json == {'type': 'integer', 'format': 'int64'}


def test_type2json_invalid():
    class MyType:
        pass

    parser = SchemaParser([])
    with pytest.raises(InvalidTypeException):
        parser._type2json(MyType)


def test_enum2json():
    class MyEnum(Enum):
        FIELD_1 = 0
        FIELD_2 = 1
        FIELD_3 = 2

    parser = SchemaParser([])
    json_type = parser._enum2json(MyEnum)
    assert json_type == {
        'type': 'string', 'enum': ['FIELD_1', 'FIELD_2', 'FIELD_3']
    }


def test_list2json():
    @dataclass
    class MyClass:
        list_field: List[str]

    parser = SchemaParser([])
    with patch.object(parser, '_type2json'):
        list_field = MyClass.__dataclass_fields__['list_field']
        list_json = parser._list2json(list_field.type)

        assert list_json['type'] == 'array'
        assert 'items' in list_json.keys()
        assert list_json == {
            'type': 'array', 'items': parser._type2json.return_value
        }
        parser._type2json.assert_called_once_with(str)


def test_field2json():
    @dataclass
    class MyClass:
        str_field: str = field(metadata={'format': 'uuid'})
        int_field: int

    parser = SchemaParser([])
    fields = MyClass.__dataclass_fields__
    str_json = parser._field2json(fields['str_field'])
    int_json = parser._field2json(fields['int_field'])

    assert str_json == {'type': 'string', 'format': 'uuid'}
    assert int_json == {'type': 'integer', 'format': 'int32'}
