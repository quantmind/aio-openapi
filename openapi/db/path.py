from aiohttp import web

from sqlalchemy.sql import and_

from .compile import compile_query
from ..spec.path import ApiPath


class SqlApiPath(ApiPath):
    """An OpenAPI path backed by an SQL model
    """

    table = None
    filters = {}
    # sql table name

    @property
    def db(self):
        """Database connection pool
        """
        return self.request.app['db']

    @property
    def db_table(self):
        return self.request.app['metadata'].tables[self.table]

    async def get_list(self, query=None):
        """Get a list of models
        """
        params = dict(self.request.query)
        params.update(query or ())
        limit = params.pop('limit', None)
        page = int(params.pop('page', 1))
        params = self.cleaned('query_schema', params)
        query = self.get_query(self.db_table.select(), params)

        # pagination
        if limit is not None:
            limit = int(limit)
            query = query.offset((page - 1) * limit)
            query = query.limit(limit)

        sql, args = compile_query(query)
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        return self.dump('response_schema', values)

    async def create_one(self):
        """Create a model
        """
        data = self.cleaned('body_schema', await self.json_data())
        statement, args = self.get_insert(data)
        async with self.db.acquire() as db:
            async with db.transaction():
                values = await db.fetch(statement, *args)
        data = ((c.name, v) for c, v in zip(self.db_table.columns, values[0]))
        return self.dump('response_schema', data)

    async def create_list(self, bodies=None):
        """Create multiple models
        """
        meta = self.request.app['metadata']
        table = meta.tables[self.table]
        bodies = bodies or await self.json_data()
        data = []
        async with self.db.acquire() as db:
            async with db.transaction():
                for body in bodies:
                    cleaned_body = self.cleaned('body_schema', body)
                    statement, args = self.get_insert(cleaned_body)
                    values = await db.fetch(statement, *args)
                    data.append(
                        (c.name, v) for c, v in zip(table.columns, values[0])
                    )

        return self.dump('response_schema', data)

    async def get_one(self, match_query=None):
        """Get a single model
        """
        filters = self.cleaned('path_schema', self.request.match_info)
        query = self.get_query(self.db_table.select(), filters)
        sql, args = compile_query(query)
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        if not values:
            raise web.HTTPNotFound()
        return self.dump('response_schema', values[0])

    async def update_one(self, data=None, match_query=None):
        """Update a single model
        """
        data = self.cleaned('body_schema', await self.json_data())
        filters = self.cleaned('path_schema', self.request.match_info)
        update = self.get_query(
                self.db_table.update(), filters
            ).values(**data).returning(*self.db_table.columns)
        sql, args = compile_query(update)
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        if not values:
            raise web.HTTPNotFound()
        return self.dump('response_schema', values[0])

    async def delete_one(self):
        """delete a single model
        """
        filters = self.cleaned('path_schema', self.request.match_info)
        delete = self.get_query(self.db_table.delete(), filters)
        sql, args = compile_query(delete.returning(*self.db_table.columns))
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        if not values:
            raise web.HTTPNotFound()

    async def delete_list(self, field, value):
        """delete multiple models
        """
        table = self.request.app['metadata'].tables[self.table]
        delete = table.delete().where(table.c[field] == value)
        sql, args = compile_query(delete.returning(*table.columns))
        async with self.db.acquire() as db:
            async with db.transaction():
                await db.fetch(sql, *args)

    # UTILITIES

    def get_insert(self, record):
        exp = (self.db_table.insert()
               .values(**record)
               .returning(*self.db_table.columns))
        return compile_query(exp)

    def get_query(self, query, params=None):
        filters = []
        columns = self.db_table.c
        params = params or {}
        for key, value in params.items():
            bits = key.split(':')
            field = bits[0]
            op = bits[1] if len(bits) == 2 else 'eq'
            if field in self.filters:
                result = self.filters[field](self, op, value)
            else:
                field = getattr(columns, field)
                result = self.filter_field(field, op, value)
            if result is not None:
                if not isinstance(result, (list, tuple)):
                    result = (result,)
                filters.extend(result)
        if filters:
            filters = and_(*filters) if len(result) > 1 else filters[0]
            query = query.where(filters)
        return query

    def filter_field(self, field, op, value):
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
