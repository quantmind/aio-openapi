from sqlalchemy import or_
from sqlalchemy.sql import and_, Select

from ..db.container import Database
from .compile import compile_query
from ..spec.pagination import DEF_PAGINATION_LIMIT


class CrudDB(Database):

    @classmethod
    def get_order_clause(cls, table, query, order_by, order_desc):
        if not order_by:
            return query

        order_by_column = getattr(table.c, order_by)
        if order_desc:
            order_by_column = order_by_column.desc()
        return query.order_by(order_by_column)

    @classmethod
    def get_search_clause(cls, table, query, search, search_columns):
        if not search:
            return query

        columns = [getattr(table.c, col) for col in search_columns]
        return query.where(
            or_(
                *(col.ilike(f'%{search}%') for col in columns)
            )
        )

    async def db_select(self, table, filters, *, conn=None, consumer=None):
        query = self.get_query(table, table.select(), consumer, filters)
        sql, args = compile_query(query)
        async with self.ensure_connection(conn) as conn:
            return await conn.fetch(sql, *args)

    async def db_delete(self, table, filters, *, conn=None, consumer=None):
        query = self.get_query(table, table.delete(), consumer, filters)
        sql, args = compile_query(query.returning(*table.columns))
        async with self.ensure_connection(conn) as conn:
            return await conn.fetch(sql, *args)

    async def db_insert(self, table, data, *, conn=None):
        async with self.ensure_connection(conn) as conn:
            statement, args = self.get_insert(table, data)
            return await conn.fetch(statement, *args)

    def get_insert(self, table, records):
        if isinstance(records, dict):
            records = [records]
        exp = table.insert(records).returning(*table.columns)
        return compile_query(exp)

    def get_query(
            self,
            table,
            query,
            consumer=None,
            params=None,
    ):
        filters = []
        columns = table.c
        params = params or {}
        limit = params.pop('limit', DEF_PAGINATION_LIMIT)
        offset = params.pop('offset', 0)
        order_by = params.pop('order_by', None)
        order_desc = params.pop('order_desc', False)
        search = params.pop('search', None)
        search_columns = params.pop('search_fields', [])
        for key, value in params.items():
            bits = key.split(':')
            field = bits[0]
            op = bits[1] if len(bits) == 2 else 'eq'
            filter_field = getattr(consumer, f'filter_{field}', None)
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

            # search
            query = self.get_search_clause(
                table,
                query,
                search,
                search_columns
            )

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
