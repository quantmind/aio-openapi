import re

from aiohttp import web
from asyncpg.exceptions import UniqueViolationError

from openapi.db.dbmodel import CrudDB
from .compile import compile_query
from ..spec.path import ApiPath


unique_regex = re.compile(r'Key \((?P<column>\w+)\)=\((?P<value>.+)\)')


class SqlApiPath(ApiPath):
    """An OpenAPI path backed by an SQL model
    """

    table = None
    # sql table name

    @property
    def db(self) -> CrudDB:
        """Database connection pool
        """
        return self.request.app['db']

    @property
    def db_table(self):
        return self.db.metadata.tables[self.table]

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
        query = self.db.get_query(self, table, table.select(), filters)

        sql, args = compile_query(query)
        async with self.db.ensure_connection(conn) as conn:
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
        statement, args = self.db.get_insert(table, data)

        async with self.db.ensure_connection(conn) as conn:
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
        values = await self.db.db_insert(table, data)
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
        values = await self.db.db_select(self, table, filters, conn=conn)
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
        update = self.db.get_query(
                self, table, table.update(), filters
            ).values(**data).returning(*table.columns)
        sql, args = compile_query(update)

        async with self.db.ensure_connection(conn) as conn:
            try:
                values = await conn.fetch(sql, *args)
            except UniqueViolationError as exc:
                self.handle_unique_violation(exc)
        if not values:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, values[0])

    async def delete_one(self, *, filters=None, table=None, conn=None):
        """delete a single model
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.cleaned('path_schema', self.request.match_info)
        values = await self.db.db_delete(self, table, filters, conn=conn)
        if not values:
            raise web.HTTPNotFound()

    async def delete_list(
            self, *, filters=None, query=None, table=None, conn=None):
        """delete multiple models
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.get_filters(query=query)
        return await self.db.db_delete(self, table, filters, conn=conn)

    def handle_unique_violation(self, exception):
        match = re.match(unique_regex, exception.detail)
        if not match:   # pragma: no cover
            raise exception

        column = match.group('column')
        message = f'{column} already exists'
        self.raiseValidationError(message=message)
