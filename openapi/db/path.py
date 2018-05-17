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

    async def get_list(self):
        """Get a list of models
        """
        querystring = dict(self.request.query)
        limit = querystring.pop('limit', None)
        page = int(querystring.pop('page', 1))
        query = self.get_query().filter_by(**querystring)

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

    async def get_one(self):
        """Get a single model
        """
        query_id = self.request.match_info['id']
        query = self.get_query().filter_by(id=query_id)
        sql, args = self.compile_query(query.statement)
        async with self.db.acquire() as db:
            values = await db.fetch(sql, *args)
        if not values:
            raise web.HTTPNotFound()
        return self.dump('response_schema', values[0])

    async def update_one(self):
        """Update a single model
        """
        query_id = self.request.match_info['id']
        table = self.request.app['metadata'].tables[self.table]
        data = self.cleaned('body_schema', await self.json_data())
        update = table.update().where(table.c.id == query_id).values(**data)
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
