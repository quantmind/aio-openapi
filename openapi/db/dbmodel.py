from sqlalchemy.sql import and_, Select

from ..utils import asynccontextmanager
from ..spec.pagination import DEF_PAGINATION_LIMIT
from .compile import compile_query


class DbModelMixin:

    table = None
    # sql table name
    db = None
    # database connection pool
    db_table = None
    # database table

    @classmethod
    def get_order_clause(cls, table, query, order_by, order_desc):
        if not order_by:
            return query

        order_by_column = getattr(table.c, order_by)
        if order_desc:
            order_by_column = order_by_column.desc()
        return query.order_by(order_by_column)

    @asynccontextmanager
    async def ensure_connection(self, conn):
        if conn:
            yield conn
        else:
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    yield conn

    async def db_select(self, filters, *, table=None, conn=None):
        table = table if table is not None else self.db_table
        query = self.get_query(table.select(), filters, table=table)
        sql, args = compile_query(query)
        async with self.ensure_connection(conn) as conn:
            return await conn.fetch(sql, *args)

    async def db_delete(self, filters, *, table=None, conn=None):
        table = table if table is not None else self.db_table
        query = self.get_query(table.delete(), filters, table=table)
        sql, args = compile_query(query.returning(*table.columns))
        async with self.ensure_connection(conn) as conn:
            return await conn.fetch(sql, *args)

    def get_insert(self, records, *, table=None):
        if isinstance(records, dict):
            records = [records]
        table = table if table is not None else self.db_table
        exp = table.insert(records).returning(*table.columns)
        return compile_query(exp)

    def get_query(self, query, params=None, table=None):
        filters = []
        table = table if table is not None else self.db_table
        columns = table.c
        params = params or {}
        limit = params.pop('limit', DEF_PAGINATION_LIMIT)
        offset = params.pop('offset', 0)
        order_by = params.pop('order_by', None)
        order_desc = params.pop('order_desc', False)
        for key, value in params.items():
            bits = key.split(':')
            field = bits[0]
            op = bits[1] if len(bits) == 2 else 'eq'
            filter_field = getattr(self, f'filter_{field}', None)
            if filter_field:
                result = filter_field(op, value)
            else:
                field = getattr(columns, field)
                result = self.default_filter_field(field, op, value)
            if result is not None:
                if not isinstance(result, (list, tuple)):
                    result = (result,)
                filters.extend(result)
        if filters:
            filters = and_(*filters) if len(filters) > 1 else filters[0]
            query = query.where(filters)

        if isinstance(query, Select):
            # ordering
            query = self.get_order_clause(table, query, order_by, order_desc)

            # pagination
            query = query.offset(offset)
            query = query.limit(limit)

        return query

    def default_filter_field(self, field, op, value):
        """
        Applies a filter on a field.

        Notes on 'ne' op:

        Example data: [None, 'john', 'roger']
        ne:john would return only roger (i.e. nulls excluded)
        ne:     would return john and roger

        Notes on  'search' op:

        For some reason, SQLAlchemy uses to_tsquery rather than
        plainto_tsquery for the match operator

        to_tsquery uses operators (&, |, ! etc.) while
        plainto_tsquery tokenises the input string and uses AND between
        tokens, hence plainto_tsquery is what we want here

        For other database back ends, the behaviour of the match
        operator is completely different - see:
        http://docs.sqlalchemy.org/en/rel_1_0/core/sqlelement.html

        :param field: field name
        :param op: 'eq', 'ne', 'gt', 'lt', 'ge', 'le' or 'search'
        :param value: comparison value, string or list/tuple
        :return:
        """
        multiple = isinstance(value, (list, tuple))

        if value == '':
            value = None

        if multiple and op in ('eq', 'ne'):
            if op == 'eq':
                return field.in_(value)
            elif op == 'ne':
                return ~field.in_(value)
        else:
            if multiple:
                assert len(value) > 0
                value = value[0]

            if op == 'eq':
                return field == value
            elif op == 'ne':
                return field != value
            elif op == 'gt':
                return field > value
            elif op == 'ge':
                return field >= value
            elif op == 'lt':
                return field < value
            elif op == 'le':
                return field <= value


class DbModel(DbModelMixin):

    def __init__(self, app, table):
        self.app = app
        self.table = table

    @property
    def db(self):
        """Database connection pool
        """
        return self.app['db']

    @property
    def db_table(self):
        return self.app['metadata'].tables[self.table]
