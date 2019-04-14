from sqlalchemy.sql import and_

from ..db.container import Database
from .compile import compile_query, count


class CrudDB(Database):
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

    async def db_count(self, table, filters, *, conn=None, consumer=None):
        query = self.get_query(table, table.select(), consumer, filters)
        sql, args = count(query)
        async with self.ensure_connection(conn) as conn:
            total = await conn.fetchrow(sql, *args)
        return total[0]

    async def db_insert(self, table, data, *, conn=None):
        async with self.ensure_connection(conn) as conn:
            statement, args = self.get_insert(table, data)
            return await conn.fetch(statement, *args)

    def get_insert(self, table, records):
        if isinstance(records, dict):
            records = [records]
        exp = table.insert(records).returning(*table.columns)
        return compile_query(exp)

    def get_query(self, table, query, consumer=None, params=None):
        filters = []
        columns = table.c
        params = params or {}

        for key, value in params.items():
            bits = key.split(":")
            field = bits[0]
            op = bits[1] if len(bits) == 2 else "eq"
            filter_field = getattr(consumer, f"filter_{field}", None)
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

        if value == "":
            value = None

        if multiple and op in ("eq", "ne"):
            if op == "eq":
                return field.in_(value)
            elif op == "ne":
                return ~field.in_(value)
        else:
            if multiple:
                assert len(value) > 0
                value = value[0]

            if op == "eq":
                return field == value
            elif op == "ne":
                return field != value
            elif op == "gt":
                return field > value
            elif op == "ge":
                return field >= value
            elif op == "lt":
                return field < value
            elif op == "le":
                return field <= value
