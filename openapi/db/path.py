import re

from aiohttp import web
from asyncpg.exceptions import UniqueViolationError
from sqlalchemy.sql import or_

from ..db.dbmodel import CrudDB
from ..spec.pagination import DEF_PAGINATION_LIMIT, Pagination
from ..spec.path import ApiPath
from .compile import compile_query, count

unique_regex = re.compile(r"Key \((?P<column>(\w+,? ?)+)\)=\((?P<value>.+)\)")


class SqlApiPath(ApiPath):
    """An OpenAPI path backed by an SQL model
    """

    table = None
    # sql table name

    @property
    def db(self) -> CrudDB:
        """Database connection pool
        """
        return self.request.app["db"]

    @property
    def db_table(self):
        return self.db.metadata.tables[self.table]

    def get_search_clause(self, table, query, search, search_columns):
        if not search:
            return query

        columns = [getattr(table.c, col) for col in search_columns]
        return query.where(or_(*(col.ilike(f"%{search}%") for col in columns)))

    def get_special_params(self, params):
        return dict(
            limit=params.pop("limit", DEF_PAGINATION_LIMIT),
            offset=params.pop("offset", 0),
            order_by=params.pop("order_by", None),
            order_desc=params.pop("order_desc", False),
            search=params.pop("search", None),
            search_columns=params.pop("search_fields", []),
        )

    async def get_list(
        self,
        *,
        filters=None,
        query=None,
        table=None,
        query_schema="query_schema",
        dump_schema="response_schema",
        conn=None,
    ):
        """Get a list of models
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.get_filters(query=query, query_schema=query_schema)
        specials = self.get_special_params(filters)
        query = self.db.get_query(table, table.select(), self, filters)
        #
        sql_count, args_count = count(query)
        #
        # order by
        if specials["order_by"]:
            order_by_column = getattr(table.c, specials["order_by"], None)
            if order_by_column is not None:
                if specials["order_desc"]:
                    order_by_column = order_by_column.desc()
                query = query.order_by(order_by_column)

        # search
        query = self.get_search_clause(
            table, query, specials["search"], specials["search_columns"]
        )

        # pagination
        offset = specials["offset"]
        limit = specials["limit"]
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        sql, args = compile_query(query)
        async with self.db.ensure_connection(conn) as conn:
            total = await conn.fetchrow(sql_count, *args_count)
            values = await conn.fetch(sql, *args)
        pagination = Pagination(self.full_url())
        data = self.dump(dump_schema, values)
        return pagination.paginated(data, total[0], offset, limit)

    async def create_one(
        self,
        *,
        data=None,
        table=None,
        body_schema="body_schema",
        dump_schema="response_schema",
        conn=None,
    ):
        """Create a model
        """
        if data is None:
            data = self.insert_data(await self.json_data(), body_schema=body_schema)
        table = table if table is not None else self.db_table
        statement, args = self.db.get_insert(table, data)

        async with self.db.ensure_connection(conn) as conn:
            try:
                values = await conn.fetch(statement, *args)
            except UniqueViolationError as exc:
                self.handle_unique_violation(exc)

        return self.dump(dump_schema, values[0])

    async def create_list(
        self,
        *,
        data=None,
        table=None,
        body_schema="body_schema",
        dump_schema="response_schema",
        conn=None,
    ):
        """Create multiple models
        """
        table = table if table is not None else self.db_table
        if data is None:
            data = await self.json_data()
        if not isinstance(data, list):
            raise web.HTTPBadRequest(
                **self.api_response_data({"message": "Invalid JSON payload"})
            )
        data = [self.insert_data(d, body_schema=body_schema) for d in data]
        values = await self.db.db_insert(table, data, conn=conn)
        return self.dump(dump_schema, values)

    async def get_one(
        self,
        *,
        filters=None,
        query=None,
        table=None,
        query_schema="query_schema",
        dump_schema="response_schema",
        conn=None,
    ):
        """Get a single model
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.get_filters(query=query, query_schema=query_schema)
        values = await self.db.db_select(table, filters, conn=conn, consumer=self)
        if not values:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, values[0])

    async def update_one(
        self,
        *,
        data=None,
        filters=None,
        query=None,
        table=None,
        body_schema="body_schema",
        query_schema="query_schema",
        dump_schema="response_schema",
        conn=None,
    ):
        """Update a single model
        """
        table = table if table is not None else self.db_table
        if data is None:
            data = self.cleaned("body_schema", await self.json_data(), strict=False)
        if not filters:
            filters = self.get_filters(query=query, query_schema=query_schema)

        if data:
            update = (
                self.db.get_query(table, table.update(), self, filters)
                .values(**data)
                .returning(*table.columns)
            )
            sql, args = compile_query(update)
            async with self.db.ensure_connection(conn) as conn:
                try:
                    values = await conn.fetch(sql, *args)
                except UniqueViolationError as exc:
                    self.handle_unique_violation(exc)
        else:
            values = await self.db.db_select(table, filters, conn=conn, consumer=self)
        if not values:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, values[0])

    async def delete_one(
        self,
        *,
        filters=None,
        query=None,
        table=None,
        query_schema="query_schema",
        conn=None,
    ):
        """delete a single model
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.get_filters(query=query, query_schema=query_schema)
        values = await self.db.db_delete(table, filters, conn=conn, consumer=self)
        if not values:
            raise web.HTTPNotFound()
        return values

    async def delete_list(self, *, filters=None, query=None, table=None, conn=None):
        """delete multiple models
        """
        table = table if table is not None else self.db_table
        if not filters:
            filters = self.get_filters(query=query)
        return await self.db.db_delete(table, filters, conn=conn, consumer=self)

    def handle_unique_violation(self, exception):
        match = re.match(unique_regex, exception.detail)
        if not match:  # pragma: no cover
            raise exception

        column = match.group("column")
        message = f"{column} already exists"
        self.raiseValidationError(message=message)
