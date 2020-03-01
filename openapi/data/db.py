import typing as t
from dataclasses import make_dataclass
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from . import fields

CONVERTERS = {}


def dataclass_from_table(
    name: str,
    table: sa.Table,
    *,
    exclude: t.Optional[t.Sequence[str]] = None,
    include: t.Optional[t.Sequence[str]] = None,
    required: bool = False,
    ops: t.Optional[t.Dict[str, t.Sequence[str]]] = None,
) -> type:
    """Create a dataclass from an :class:`sqlalchemy.schema.Table`

    :param name: dataclass name
    :param table: sqlalchemy table
    :param exclude: fields to exclude from the dataclass
    :param include: fields to include in the dataclass
    :param required: set all non nullable columns as required fields in the dataclass
    :param ops: additional operation for fields
    """
    columns = []
    include = set(include or table.columns.keys()) - set(exclude or ())
    column_ops = t.cast(t.Dict[str, t.Sequence[str]], ops or {})
    for col in table.columns:
        if col.name not in include:
            continue
        ctype = type(col.type)
        converter = CONVERTERS.get(ctype)
        if not converter:  # pragma:   no cover
            raise NotImplementedError(f"Cannot convert column {col.name}: {ctype}")
        field = (col.name, *converter(col, required, column_ops.get(col.name, ())))
        columns.append(field)
    return make_dataclass(name, columns)


def converter(*types):
    def _(f):
        for type_ in types:
            CONVERTERS[type_] = f
        return f

    return _


@converter(sa.Boolean)
def bl(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.bool_field)
    return (bool, data_field(**info(col, required, ops)))


@converter(sa.Integer)
def integer(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.number_field)
    return (int, data_field(precision=0, **info(col, required, ops)))


@converter(sa.Numeric)
def number(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.decimal_field)
    return (Decimal, data_field(precision=col.type.scale, **info(col, required, ops)))


@converter(sa.String, sa.Text, sa.CHAR, sa.VARCHAR)
def string(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.str_field)
    return (
        str,
        data_field(max_length=col.type.length or 0, **info(col, required, ops)),
    )


@converter(sa.DateTime)
def dt_ti(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.date_time_field)
    return (
        datetime,
        data_field(timezone=col.type.timezone, **info(col, required, ops)),
    )


@converter(sa.Date)
def dt(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.date_field)
    return (date, data_field(**info(col, required, ops)))


@converter(sa.Enum)
def en(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.enum_field)
    return (
        col.type.enum_class,
        data_field(col.type.enum_class, **info(col, required, ops)),
    )


@converter(sa.JSON)
def js(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.json_field)
    val = None
    if col.default:
        arg = col.default.arg
        val = arg() if col.default.is_callable else arg
    return (JsonTypes.get(type(val), t.Dict), data_field(**info(col, required, ops)))


@converter(UUIDType)
def uuid(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data_field = col.info.get("data_field", fields.uuid_field)
    return (str, data_field(**info(col, required, ops)))


def info(col: sa.Column, required: bool, ops: t.Sequence[str]) -> t.Tuple:
    data = dict(
        description=col.doc,
        required=not col.nullable if required is not False else False,
        ops=ops,
    )
    data.update(col.info)
    data.pop("data_field", None)
    return data


JsonTypes = {list: t.List, dict: t.Dict}
