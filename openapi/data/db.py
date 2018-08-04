from datetime import datetime
from dataclasses import make_dataclass
from decimal import Decimal

import sqlalchemy as sa

from sqlalchemy_utils import UUIDType

from . import fields


CONVERTERS = {}


def dataclass_from_table(name, table):
    columns = []
    for col in table.columns:
        ctype = type(col.type)
        converter = CONVERTERS.get(ctype)
        if not converter:
            raise NotImplementedError(
                f'Cannot convert column {col.name}: {ctype}')
        field = (col.name, *converter(col))
        columns.append(field)
    return make_dataclass(name, columns)


def converter(*types):
    def _(f):
        for type_ in types:
            CONVERTERS[type_] = f
        return f

    return _


@converter(sa.Integer)
def integer(col):
    return (int, fields.number_field(precision=0, **info(col)))


@converter(sa.Numeric)
def number(col):
    return (
        Decimal, fields.number_field(
            precision=col.type.scale, **info(col)
        )
    )


@converter(sa.String, sa.Text)
def string(col):
    return (str, fields.data_field(**info(col)))


@converter(sa.DateTime)
def dt(col):
    return (datetime, fields.date_time_field(**info(col)))


@converter(sa.Enum)
def en(col):
    return (
        col.type.enum_class,
        fields.enum_field(col.type.enum_class, **info(col))
    )


@converter(UUIDType)
def uiid(col):
    return (
        str,
        fields.uuid_field(**info(col))
    )


def info(col):
    return dict(
        description=col.doc,
        required=not col.nullable
    )
