import re
from typing import Dict, List, Optional, Sequence, cast

import sqlalchemy as sa
from aiohttp import web
from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError
from sqlalchemy.sql import or_

from ..data.pagination import PaginatedData, Pagination
from ..db.dbmodel import CrudDB
from ..spec.path import ApiPath
from ..types import DataType, Records, SchemaTypeOrStr, StrDict
from .compile import Select, Update, compile_query, count

unique_regex = re.compile(r"Key \((?P<column>(\w+,? ?)+)\)=\((?P<value>.+)\)")


class SqlApiPath(ApiPath):
    """An :class:`.ApiPath` backed by an SQL model
    """

    table: str = ""
    """sql table name"""

    @property
    def db(self) -> CrudDB:
        """Database connection pool
        """
        return self.request.app["db"]

    @property
    def db_table(self) -> sa.Table:
        """Default database table for this route"""
        return self.db.metadata.tables[self.table]

    def get_search_clause(
        self, table: sa.Table, query: Select, search: str, search_fields: Sequence[str]
    ) -> Select:
        if not search:
            return query

        columns = [getattr(table.c, col) for col in search_fields]
        return query.where(or_(*(col.ilike(f"%{search}%") for col in columns)))

    async def get_list(
        self,
        *,
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        query_schema: SchemaTypeOrStr = "query_schema",
        dump_schema: SchemaTypeOrStr = "response_schema",
        conn: Optional[Connection] = None,
    ) -> PaginatedData:
        """Get a list of models

        :param filters: dictionary of filters, if not provided it will be created from
            the query_schema
        :param query: additional query paraeters, only used when filters is not provided
        :param table: sqlalchemy table, if not provided the default :attr:`.db_table` is
            used instead
        """
        table = table if table is not None else self.db_table
        if filters is None:
            filters = self.get_filters(query=query, query_schema=query_schema)
        specials = self.get_special_params(cast(Dict, filters))
        sql_query = cast(
            Select, self.db.get_query(table, table.select(), self, filters)
        )
        #
        sql_count, args_count = count(sql_query)
        #
        # order by
        if specials["order_by"]:
            order_by_column = getattr(table.c, specials["order_by"], None)
            if order_by_column is not None:
                if specials["order_desc"]:
                    order_by_column = order_by_column.desc()
                sql_query = sql_query.order_by(order_by_column)

        # search
        sql_query = self.get_search_clause(
            table, sql_query, specials["search"], specials["search_fields"]
        )

        # pagination
        offset = specials["offset"]
        limit = specials["limit"]
        if offset:
            sql_query = sql_query.offset(offset)
        if limit:
            sql_query = sql_query.limit(limit)

        sql, args = compile_query(sql_query)
        async with self.db.ensure_connection(conn) as conn:
            total = await conn.fetchrow(sql_count, *args_count)
            values = await conn.fetch(sql, *args)
        pagination = Pagination(self.full_url())
        data = cast(List[StrDict], self.dump(dump_schema, values))
        return pagination.paginated(data, total[0], offset, limit)

    async def create_one(
        self,
        *,
        data: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        body_schema: SchemaTypeOrStr = "body_schema",
        dump_schema: SchemaTypeOrStr = "response_schema",
        conn: Optional[Connection] = None,
    ) -> StrDict:
        """Create a new database model

        :param data: input data, if not given it loads it via :meth:`.json_data`
        :param table: sqlalchemy table, if not given it uses the
            default :attr:`db_table`
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

        return cast(StrDict, self.dump(dump_schema, values[0]))

    async def create_list(
        self,
        *,
        data: Optional[DataType] = None,
        table: Optional[sa.Table] = None,
        body_schema: SchemaTypeOrStr = "body_schema",
        dump_schema: SchemaTypeOrStr = "response_schema",
        conn: Optional[Connection] = None,
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
        schema = self.get_schema(body_schema)
        assert schema.container is list
        data = [self.insert_data(d, body_schema=schema.element) for d in data]
        values = await self.db.db_insert(table, data, conn=conn)
        return self.dump(dump_schema, values)

    async def get_one(
        self,
        *,
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        query_schema: SchemaTypeOrStr = "query_schema",
        dump_schema: SchemaTypeOrStr = "response_schema",
        conn: Optional[Connection] = None,
    ):
        """Get a single model
        """
        table = table if table is not None else self.db_table
        if filters is None:
            filters = self.get_filters(query=query, query_schema=query_schema)
        values = await self.db.db_select(table, filters, conn=conn, consumer=self)
        if not values:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, values[0])

    async def update_one(
        self,
        *,
        data: Optional[StrDict] = None,
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        body_schema: SchemaTypeOrStr = "body_schema",
        query_schema: SchemaTypeOrStr = "query_schema",
        dump_schema: SchemaTypeOrStr = "response_schema",
        conn: Optional[Connection] = None,
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
                cast(Update, self.db.get_query(table, table.update(), self, filters))
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
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        query_schema: SchemaTypeOrStr = "query_schema",
        conn: Optional[Connection] = None,
    ) -> Records:
        """Delete a single model
        """
        table = table if table is not None else self.db_table
        if filters is None:
            filters = self.get_filters(query=query, query_schema=query_schema)
        values = await self.db.db_delete(table, filters, conn=conn, consumer=self)
        if not values:
            raise web.HTTPNotFound
        return values

    async def delete_list(
        self,
        *,
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        conn: Optional[Connection] = None,
    ) -> Records:
        """delete multiple models
        """
        table = table if table is not None else self.db_table
        if filters is None:
            filters = self.get_filters(query=query)
        return await self.db.db_delete(table, filters, conn=conn, consumer=self)

    def handle_unique_violation(self, exception):
        match = re.match(unique_regex, exception.detail)
        if not match:  # pragma: no cover
            raise exception

        column = match.group("column")
        message = f"{column} already exists"
        self.raiseValidationError(message=message)
