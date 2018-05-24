from aiohttp import web

from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import postgresql

from .compile import execute_defaults
from ..spec.path import ApiPath


Session = sessionmaker()


class SqlApiPath(ApiPath):
    """An OpenAPI path backed by an SQL model
    """

    table = None
    # sql table name
    dialect = postgresql.dialect()
    # sql dialect

    @property
    def db(self):
        """Database connection pool
        """
        return self.request.app['db']

    async def get_list(self, query=None):
        """Get a list of models
        """
        querystring = dict(self.request.query)
        querystring.update(query or {})
        limit = querystring.pop('limit', None)
        page = int(querystring.pop('page', 1))
        cleaned_query = self.cleaned('query_schema', querystring)
        query = self.get_query().filter_by(**cleaned_query)

        # pagination
        if limit is not None:
            limit = int(limit)
            query = query.offset((page - 1) * limit)
            query = query.limit(limit)

        sql, args = self.compile_query(query.statement)
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        return self.dump('response_schema', values)

    async def create_one(self):
        """Create a model
        """
        meta = self.request.app['metadata']
        table = meta.tables[self.table]
        data = self.cleaned('body_schema', await self.json_data())
        statement, args = self.get_insert(data)
        async with self.db.acquire() as db:
            async with db.transaction():
                values = await db.fetch(statement, *args)
        data = ((c.name, v) for c, v in zip(table.columns, values[0]))
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
        match_query = match_query or {'id': self.request.match_info['id']}
        query = self.get_query().filter_by(**match_query)
        sql, args = self.compile_query(query.statement)
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        if not values:
            raise web.HTTPNotFound()
        return self.dump('response_schema', values[0])

    async def update_one(self, data=None, match_query=None):
        """Update a single model
        """
        match_query = match_query or {'id': self.request.match_info['id']}
        table = self.request.app['metadata'].tables[self.table]
        data = self.cleaned('body_schema', data or await self.json_data())
        update = table.update()
        for field, value in match_query.items():
            update = update.where(table.c[field] == value)
        update = update.values(**data)

        sql, args = self.compile_query(update.returning(*table.columns))
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        if not values:
            raise web.HTTPNotFound()
        return self.dump('response_schema', values[0])

    async def delete_one(self):
        """delete a single model
        """
        query_id = self.request.match_info['id']
        table = self.request.app['metadata'].tables[self.table]
        delete = table.delete().where(table.c.id == query_id)
        sql, args = self.compile_query(delete.returning(*table.columns))
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        if not values:
            raise web.HTTPNotFound()
        return None

    async def delete_list(self, field, value):
        """delete multiple models
        """
        table = self.request.app['metadata'].tables[self.table]
        delete = table.delete().where(table.c[field] == value)
        sql, args = self.compile_query(delete.returning(*table.columns))
        async with self.db.acquire() as db:
            async with db.transaction():
                await db.fetch(sql, *args)
        return None

    # UTILITIES

    def get_query(self):
        meta = self.request.app['metadata']
        table = meta.tables[self.table]
        session = Session()
        return session.query(table)

    def get_insert(self, record):
        meta = self.request.app['metadata']
        table = meta.tables[self.table]
        exp = table.insert().values(**record).returning(*table.columns)
        return self.compile_query(exp)

    def compile_query(self, query, inline=False):
        execute_defaults(query)
        compiled = query.compile(dialect=self.dialect)
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
