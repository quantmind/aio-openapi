from aiohttp import web

from sqlalchemy.sql import and_

from .compile import compile_query
from ..spec.path import ApiPath
from ..spec.pagination import DEF_PAGINATION_LIMIT
from ..utils import asynccontextmanager


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

    async def get_list(
        self, query=None, table=None, query_schema='query_schema',
        dump_schema='response_schema', conn=None
    ):
        """Get a list of models
        """
        table = table if table is not None else self.db_table
        params = self.get_filters(query=query, query_schema=query_schema)
        limit = params.pop('limit', DEF_PAGINATION_LIMIT)
        offset = params.pop('offset', 0)
        query = self.get_query(table.select(), params, table=table)

        # pagination
        query = query.offset(offset)
        query = query.limit(limit)

        sql, args = compile_query(query)
        async with self.ensure_connection(conn) as conn:
            values = await conn.fetch(sql, *args)

        return self.dump(dump_schema, values)

    async def create_one(
        self, data=None, table=None, body_schema='body_schema',
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
            values = await conn.fetch(statement, *args)

        data = ((c.name, v) for c, v in zip(table.columns, values[0]))
        return self.dump(dump_schema, data)

    async def create_list(self, data=None, conn=None):
        """Create multiple models
        """
        if data is None:
            data = await self.json_data()
        if not isinstance(data, list):
            raise web.HTTPBadRequest(
                **self.api_response_data({'message': 'Invalid JSON payload'})
            )
        data = [self.insert_data(d) for d in data]
        cols = self.db_table.columns

        async with self.ensure_connection(conn) as conn:
            statement, args = self.get_insert(data)
            values = await conn.fetch(statement, *args)

        result = [
            ((c.name, v) for c, v in zip(cols, value))
            for value in values
        ]
        return self.dump('response_schema', result)

    async def get_one(
        self, query=None, table=None, query_schema='query_schema',
        dump_schema='response_schema', conn=None
    ):
        """Get a single model
        """
        table = table if table is not None else self.db_table
        filters = self.get_filters(query=query, query_schema=query_schema)
        query = self.get_query(table.select(), filters, table=table)
        sql, args = compile_query(query)

        async with self.ensure_connection(conn) as conn:
            values = await conn.fetch(sql, *args)

        if not values:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, values[0])

    async def update_one(self, data=None, conn=None):
        """Update a single model
        """
        if data is None:
            data = self.cleaned('body_schema', await self.json_data(), False)
        filters = self.cleaned('path_schema', self.request.match_info)
        update = self.get_query(
                self.db_table.update(), filters
            ).values(**data).returning(*self.db_table.columns)
        sql, args = compile_query(update)

        async with self.ensure_connection(conn) as conn:
            values = await conn.fetch(sql, *args)

        if not values:
            raise web.HTTPNotFound()
        return self.dump('response_schema', values[0])

    async def delete_one(self, conn=None):
        """delete a single model
        """
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
