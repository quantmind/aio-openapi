import re

from aiohttp import web
from asyncpg.exceptions import UniqueViolationError
from sqlalchemy.sql import and_, Select

from .compile import compile_query
from ..spec.pagination import DEF_PAGINATION_LIMIT
from ..spec.path import ApiPath
from ..utils import asynccontextmanager

unique_regex = re.compile(r'Key \((?P<column>\w+)\)=\((?P<value>.+)\)')


class SqlApiPath(ApiPath):
    """An OpenAPI path backed by an SQL model
    """

    table = None
    # sql table name

    @property
    def db(self):
        """Database connection pool
        """
        return self.request.app['db']

    @property
    def db_table(self):
        return self.request.app['metadata'].tables[self.table]

    @asynccontextmanager
    async def ensure_connection(self, conn):
        if conn:
            yield conn
        else:
            async with self.db.acquire() as conn:
                async with conn.transaction():
                    yield conn

    @staticmethod
    def get_order_clause(table, query, order_by, order_desc):
        if not order_by:
            return query

        order_by_column = getattr(table.c, order_by)
        if order_desc:
            order_by_column = order_by_column.desc()
        return query.order_by(order_by_column)

    async def get_list(
            self, *, filters=None, query=None, table=None,
            query_schema='query_schema', dump_schema='response_schema',
            conn=None
    ):
        """Get a list of models
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.get_filters(query=query, query_schema=query_schema)
        query = self.get_query(table.select(), filters, table=table)

        sql, args = compile_query(query)
        async with self.ensure_connection(conn) as conn:
            values = await conn.fetch(sql, *args)
        return self.dump(dump_schema, values)

    async def create_one(
        self, *, data=None, table=None, body_schema='body_schema',
        dump_schema='response_schema', conn=None
    ):
        """Create a model
        """
        if data is None:
            data = self.insert_data(
                await self.json_data(), body_schema=body_schema
            )
        table = table if table is not None else self.db_table
        statement, args = self.get_insert(data, table=table)

        async with self.ensure_connection(conn) as conn:
            try:
                values = await conn.fetch(statement, *args)
            except UniqueViolationError as exc:
                self.handle_unique_violation(exc)

        return self.dump(dump_schema, values[0])

    async def create_list(
        self, *, data=None, table=None, body_schema='body_schema',
        dump_schema='response_schema', conn=None
    ):
        """Create multiple models
        """
        table = table if table is not None else self.db_table
        if data is None:
            data = await self.json_data()
        if not isinstance(data, list):
            raise web.HTTPBadRequest(
                **self.api_response_data({'message': 'Invalid JSON payload'})
            )
        data = [self.insert_data(d, body_schema=body_schema) for d in data]

        async with self.ensure_connection(conn) as conn:
            statement, args = self.get_insert(data, table=table)
            values = await conn.fetch(statement, *args)

        return self.dump(dump_schema, values)

    async def get_one(
        self, *, filters=None, query=None, table=None,
        query_schema='query_schema',
        dump_schema='response_schema', conn=None
    ):
        """Get a single model
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.get_filters(query=query, query_schema=query_schema)
        query = self.get_query(table.select(), filters, table=table)
        sql, args = compile_query(query)

        async with self.ensure_connection(conn) as conn:
            values = await conn.fetch(sql, *args)

        if not values:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, values[0])

    async def update_one(
        self, *, data=None, filters=None, table=None,
        body_schema='body_schema', dump_schema='response_schema', conn=None
    ):
        """Update a single model
        """
        table = table if table is not None else self.db_table
        if data is None:
            data = self.cleaned(
                'body_schema', await self.json_data(), strict=False)
        if not filters:
            filters = self.cleaned('path_schema', self.request.match_info)
        update = self.get_query(
                table.update(), filters
            ).values(**data).returning(*table.columns)
        sql, args = compile_query(update)

        async with self.ensure_connection(conn) as conn:
            try:
                values = await conn.fetch(sql, *args)
            except UniqueViolationError as exc:
                self.handle_unique_violation(exc)
        if not values:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, values[0])

    async def delete_one(self, *, filters=None, conn=None):
        """delete a single model
        """
        if not filters:
            filters = self.cleaned('path_schema', self.request.match_info)
        delete = self.get_query(self.db_table.delete(), filters)
        sql, args = compile_query(delete.returning(*self.db_table.columns))

        async with self.ensure_connection(conn) as conn:
            values = await conn.fetch(sql, *args)

        if not values:
            raise web.HTTPNotFound()

    async def delete_list(self, query=None, conn=None):
        """delete multiple models
        """
        filters = self.get_filters(query=query)
        delete = self.get_query(self.db_table.delete(), filters)
        sql, args = compile_query(delete)

        async with self.ensure_connection(conn) as conn:
            await conn.fetch(sql, *args)

    # UTILITIES

    def get_insert(self, records, table=None):
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

    def handle_unique_violation(self, exception):
        match = re.match(unique_regex, exception.detail)
        if not match:   # pragma: no cover
            raise exception

        column = match.group('column')
        message = f'{column} already exists'
        self.raiseValidationError(message=message)
