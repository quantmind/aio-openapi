from typing import Dict, List, Tuple, Union, cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import pypostgresql
from sqlalchemy.sql import Select
from sqlalchemy.sql.dml import Delete, Insert, Update

from .. import json

QueryType = Union[Delete, Update, Select]
ClauseType = Union[Insert, QueryType]

QueryTuple = Tuple[str, List]

dialect = pypostgresql.dialect(
    paramstyle="pyformat", json_serializer=json.dumps, json_deserializer=json.loads
)

dialect.implicit_returning = True
dialect.supports_native_enum = True
dialect.supports_smallserial = True  # 9.2+
dialect._backslash_escapes = False
dialect.supports_sane_multi_rowcount = True  # psycopg 2.0.9+
dialect._has_native_hstore = True


def _execute_defaults(query: Union[Insert, Update], attr_name: str) -> None:
    # query.parameters could be a list in a multi row insert
    if isinstance(query.parameters, list):
        for param in query.parameters:
            _execute_default_attr(query, param, attr_name)
    else:
        query.parameters = query.parameters or {}
        _execute_default_attr(query, query.parameters, attr_name)
    return None


def _execute_default_attr(
    query: Union[Insert, Update], param: Dict, attr_name: str
) -> None:
    for col in query.table.columns:
        attr = getattr(col, attr_name)
        if attr and param.get(col.name) is None:
            if attr.is_scalar:
                param[col.name] = attr.arg
            elif attr.is_callable:
                param[col.name] = attr.arg({})


def compile_query(query: ClauseType) -> QueryTuple:
    if isinstance(query, Insert):
        _execute_defaults(cast(Insert, query), "default")
    elif isinstance(query, Update):
        _execute_defaults(cast(Update, query), "onupdate")

    compiled = query.compile(dialect=dialect)
    compiled_params = sorted(compiled.params.items())
    #
    mapping = {key: "$" + str(i) for i, (key, _) in enumerate(compiled_params, start=1)}
    new_query = compiled.string % mapping
    processors = compiled._bind_processors
    new_params = [
        processors[key](val) if key in processors else val
        for key, val in compiled_params
    ]
    return new_query, new_params


def count(query: Select) -> QueryTuple:
    count_query = select([func.count()]).select_from(query.alias("inner"))
    return compile_query(count_query)
