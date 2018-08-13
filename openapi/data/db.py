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
    return (bool, fields.bool_field(**info(col, required)))


@converter(sa.Integer)
def integer(col, required):
    return (int, fields.number_field(precision=0, **info(col, required)))


@converter(sa.Numeric)
def number(col, required):
    return (
        Decimal, fields.number_field(
            precision=col.type.scale, **info(col, required)
        )
    )


@converter(sa.String, sa.Text, sa.CHAR, sa.VARCHAR)
def string(col, required):
    return (str, fields.str_field(
        max_length=col.type.length or 0, **info(col, required)))


@converter(sa.DateTime)
def dt_ti(col, required):
    return (datetime, fields.date_time_field(**info(col, required)))


@converter(sa.Date)
def dt(col, required):
    return (date, fields.date_field(**info(col, required)))


@converter(sa.Enum)
def en(col, required):
    return (
        col.type.enum_class,
        fields.enum_field(col.type.enum_class, **info(col, required))
    )


@converter(sa.JSON)
def js(col, required):
    val = None
    if col.default:
        arg = col.default.arg
        val = arg() if col.default.is_callable else arg
    return (
        JsonTypes.get(type(val), typing.Dict),
        fields.json_field(**info(col, required))
    )


@converter(UUIDType)
def uuid(col, required):
    return (
        str,
        fields.uuid_field(**info(col, required))
    )


def info(col, required):

    data = dict(
        description=col.doc,
        required=not col.nullable if required is not False else False
    )
    data.update(col.info)
    return data


JsonTypes = {
    list: typing.List,
    dict: typing.Dict
}
