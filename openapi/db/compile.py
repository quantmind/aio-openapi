from sqlalchemy.dialects.postgresql import pypostgresql
from sqlalchemy.sql.dml import Insert as InsertObject, Update as UpdateObject

dialect = pypostgresql.dialect(paramstyle='pyformat')

dialect.implicit_returning = True
dialect.supports_native_enum = True
dialect.supports_smallserial = True  # 9.2+
dialect._backslash_escapes = False
dialect.supports_sane_multi_rowcount = True  # psycopg 2.0.9+
dialect._has_native_hstore = True


def _execute_defaults(query):
    if isinstance(query, InsertObject):
        attr_name = 'default'
    elif isinstance(query, UpdateObject):
        attr_name = 'onupdate'
    else:
        return query

    # query.parameters could be a list in a multi row insert
    if isinstance(query.parameters, list):
        for param in query.parameters:
            _execute_default_attr(query, param, attr_name)
    else:
        query.parameters = query.parameters or {}
        _execute_default_attr(query, query.parameters, attr_name)
    return query


def _execute_default_attr(query, param, attr_name):
    for col in query.table.columns:
        attr = getattr(col, attr_name)
        if attr and param.get(col.name) is None:
            if attr.is_scalar:
                param[col.name] = attr.arg
            elif attr.is_callable:
                param[col.name] = attr.arg({})


def compile_query(query, inline=False):
    _execute_defaults(query)
    compiled = query.compile(dialect=dialect)
    compiled_params = sorted(compiled.params.items())
    #
    mapping = {
        key: '$' + str(i)
        for i, (key, _) in enumerate(compiled_params, start=1)
    }
    new_query = compiled.string % mapping
    processors = compiled._bind_processors
    new_params = [
        processors[key](val) if key in processors else val
        for key, val in compiled_params
    ]
    if inline:
        return new_query

    return new_query, new_params
