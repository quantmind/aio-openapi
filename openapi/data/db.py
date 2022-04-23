from dataclasses import Field, make_dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import partial
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from . import fields

ConverterType = Callable[[sa.Column, bool, bool, Sequence[str]], Tuple[Type, Field]]
CONVERTERS: Dict[str, ConverterType] = {}


def dataclass_from_table(
    name: str,
    table: sa.Table,
    *,
    exclude: Optional[Sequence[str]] = None,
    include: Optional[Sequence[str]] = None,
    default: Union[bool, Sequence[str]] = False,
    required: Union[bool, Sequence[str]] = False,
    ops: Optional[Dict[str, Sequence[str]]] = None,
) -> type:
    """Create a dataclass from an :class:`sqlalchemy.schema.Table`

    :param name: dataclass name
    :param table: sqlalchemy table
    :param exclude: fields to exclude from the dataclass
    :param include: fields to include in the dataclass
    :param default: use columns defaults in the dataclass
    :param required: set non nullable columns without a default as
        required fields in the dataclass
    :param ops: additional operation for fields
    """
    columns = []
    includes = set(include or table.columns.keys()) - set(exclude or ())
    defaults = column_info(includes, default)
    requireds = column_info(includes, required)
    column_ops = cast(Dict[str, Sequence[str]], ops or {})
    for col in table.columns:
        if col.name not in includes:
            continue
        ctype = type(col.type)
        converter = CONVERTERS.get(ctype)
        if not converter:  # pragma:   no cover
            raise NotImplementedError(f"Cannot convert column {col.name}: {ctype}")
        required = col.name in requireds
        use_default = col.name in defaults
        field = (
            col.name,
            *converter(col, required, use_default, column_ops.get(col.name, ())),
        )
        columns.append(field)
    return make_dataclass(name, columns)


def column_info(columns: Set[str], value: Union[bool, Sequence[str]]) -> Set[str]:
    if value is False:
        return set()
    elif value is True:
        return columns.copy()
    else:
        return set(value if value is not None else columns)


def converter(*types):
    def _(f):
        for type_ in types:
            CONVERTERS[type_] = f
        return f

    return _


@converter(sa.Boolean)
def bl(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.bool_field)
    return (bool, data_field(**info(col, required, use_default, ops)))


@converter(sa.Integer)
def integer(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.number_field)
    return (int, data_field(precision=0, **info(col, required, use_default, ops)))


@converter(sa.Numeric)
def number(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.decimal_field)
    return (
        Decimal,
        data_field(precision=col.type.scale, **info(col, required, use_default, ops)),
    )


@converter(sa.String, sa.Text, sa.CHAR, sa.VARCHAR)
def string(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.str_field)
    return (
        str,
        data_field(
            max_length=col.type.length or 0, **info(col, required, use_default, ops)
        ),
    )


@converter(sa.DateTime)
def dt_ti(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.date_time_field)
    return (
        datetime,
        data_field(timezone=col.type.timezone, **info(col, required, use_default, ops)),
    )


@converter(sa.Date)
def dt(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.date_field)
    return (date, data_field(**info(col, required, use_default, ops)))


@converter(sa.Enum)
def en(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.enum_field)
    return (
        col.type.enum_class,
        data_field(col.type.enum_class, **info(col, required, use_default, ops)),
    )


@converter(sa.JSON)
def js(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.json_field)
    val = None
    if col.default:
        arg = col.default.arg
        val = arg() if col.default.is_callable else arg
    return (
        JsonTypes.get(type(val), Dict),
        data_field(**info(col, required, use_default, ops)),
    )


@converter(UUIDType)
def uuid(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data_field = col.info.get("data_field", fields.uuid_field)
    return (str, data_field(**info(col, required, use_default, ops)))


def info(
    col: sa.Column, required: bool, use_default: bool, ops: Sequence[str]
) -> Tuple[Type, Field]:
    data = dict(ops=ops)
    if use_default:
        default = col.default.arg if col.default is not None else None
        if callable(default):
            data.update(default_factory=partial(default, None))
            required = False
        elif isinstance(default, (list, dict, set)):
            data.update(default_factory=lambda: default.copy())
            required = False
        else:
            data.update(default=default)
            if required and (col.nullable or default is not None):
                required = False
    elif required and col.nullable:
        required = False
    data.update(required=required)
    if col.doc:
        data.update(description=col.doc)
    data.update(col.info)
    data.pop("data_field", None)
    return data


JsonTypes = {list: List, dict: Dict}
