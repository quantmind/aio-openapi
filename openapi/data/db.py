import typing
from datetime import datetime, date
from dataclasses import make_dataclass
from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy_utils import UUIDType

from . import fields


CONVERTERS = {}


def dataclass_from_table(
        name, table, *, exclude=None, include=None, required=None):
    """Create a dataclass from an sqlalchemy table
    """
    columns = []
    include = set(include or table.columns.keys()) - set(exclude or ())
    for col in table.columns:
        if col.name not in include:
            continue
        ctype = type(col.type)
        converter = CONVERTERS.get(ctype)
        if not converter:   # pragma:   no cover
            raise NotImplementedError(
                f'Cannot convert column {col.name}: {ctype}')
        field = (col.name, *converter(col, required))
        columns.append(field)
    return make_dataclass(name, columns)


def converter(*types):
    def _(f):
        for type_ in types:
            CONVERTERS[type_] = f
        return f

    return _


@converter(sa.Boolean)
def bl(col, required):
    data_field = col.info.get('data_field', fields.bool_field)
    return (
        bool,
        data_field(**info(col, required))
    )


@converter(sa.Integer)
def integer(col, required):
    data_field = col.info.get('data_field', fields.number_field)
    return (
        int,
        data_field(precision=0, **info(col, required))
    )


@converter(sa.Numeric)
def number(col, required):
    data_field = col.info.get('data_field', fields.decimal_field)
    return (
        Decimal,
        data_field(precision=col.type.scale, **info(col, required))
    )


@converter(sa.String, sa.Text, sa.CHAR, sa.VARCHAR)
def string(col, required):
    data_field = col.info.get('data_field', fields.str_field)
    return (
        str,
        data_field(max_length=col.type.length or 0, **info(col, required))
    )


@converter(sa.DateTime)
def dt_ti(col, required):
    data_field = col.info.get('data_field', fields.date_time_field)
    return (
        datetime,
        data_field(**info(col, required))
    )


@converter(sa.Date)
def dt(col, required):
    data_field = col.info.get('data_field', fields.date_field)
    return (
        date,
        data_field(**info(col, required))
    )


@converter(sa.Enum)
def en(col, required):
    data_field = col.info.get('data_field', fields.enum_field)
    return (
        col.type.enum_class,
        data_field(col.type.enum_class, **info(col, required))
    )


@converter(sa.JSON)
def js(col, required):
    data_field = col.info.get('data_field', fields.json_field)
    val = None
    if col.default:
        arg = col.default.arg
        val = arg() if col.default.is_callable else arg
    return (
        JsonTypes.get(type(val), typing.Dict),
        data_field(**info(col, required))
    )


@converter(UUIDType)
def uuid(col, required):
    data_field = col.info.get('data_field', fields.uuid_field)
    return (
        str,
        data_field(**info(col, required))
    )


def info(col, required):
    data = dict(
        description=col.doc,
        required=not col.nullable if required is not False else False
    )
    data.update(col.info)
    data.pop('data_field', None)
    return data


JsonTypes = {
    list: typing.List,
    dict: typing.Dict
}
