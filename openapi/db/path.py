import re
from typing import List, Optional, Tuple, cast

import sqlalchemy as sa
from aiohttp import web
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select

from openapi.data.validate import ValidationErrors

from ..pagination import PaginatedData, Pagination, Search, create_dataclass
from ..spec.path import ApiPath
from ..types import Connection, DataType, Record, Records, SchemaTypeOrStr, StrDict
from .dbmodel import CrudDB

unique_regex = re.compile(r"Key \((?P<column>(\w+,? ?)+)\)=\((?P<value>.+)\)")


class SqlApiPath(ApiPath):
    """An :class:`.ApiPath` backed by an SQL model.

    This class provides utility methods for all CRUD operations.
    """

    table: str = ""
    """sql table name"""

    @property
    def db(self) -> CrudDB:
        """Database connection pool"""
        return self.request.app["db"]

    @property
    def db_table(self) -> sa.Table:
        """Default database table for this route.

        Obtained from the :attr:`table` attribute.
        """
        return self.db.metadata.tables[self.table]

    def get_pag_search_filters(
        self,
        *,
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        query_schema: SchemaTypeOrStr = "query_schema",
    ) -> Tuple[Pagination, Search, dict]:
        if filters is None:
            filters = self.get_filters(query=query, query_schema=query_schema)
        schema = self.get_schema(query_schema)
        pagination = create_dataclass(schema, filters, Pagination)
        search = create_dataclass(schema, filters, Search)
        return pagination, search, filters

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
        :param query: additional query parameters, only used when filters
            is not provided
        :param table: sqlalchemy table, if not provided the default :attr:`.db_table` is
            used instead
        :param conn: optional db connection
        """
        table = table if table is not None else self.db_table
        pagination, search, filters = self.get_pag_search_filters(
            filters=filters, query=query, query_schema=query_schema
        )
        sql_query = cast(
            Select,
            self.db.get_query(
                table,
                table.select(),
                params=filters,
                consumer=self,
            ),
        )
        sql_query = cast(Select, self.db.search_query(table, sql_query, search))
        try:
            values, total = await self.db.db_paginate(
                table, sql_query, pagination, conn=conn
            )
        except ValidationErrors as e:
            self.raise_validation_error(errors=e.errors)
        data = cast(List[StrDict], self.dump(dump_schema, values.all()))
        return pagination.paginated(self.full_url(), data, total)

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
        :param conn: optional db connection
        """
        if data is None:
            data = self.insert_data(await self.json_data(), body_schema=body_schema)
        table = table if table is not None else self.db_table
        sql = self.db.insert_query(table, data)

        async with self.db.ensure_connection(conn) as conn:
            try:
                result = await conn.execute(sql)
            except IntegrityError as exc:
                self.handle_unique_violation(exc)
                raise

        return cast(StrDict, self.dump(dump_schema, result.one()))

    async def create_list(
        self,
        *,
        data: Optional[DataType] = None,
        table: Optional[sa.Table] = None,
        body_schema: SchemaTypeOrStr = "body_schema",
        dump_schema: SchemaTypeOrStr = "response_schema",
        conn: Optional[Connection] = None,
    ):
        """Create multiple models"""
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
        return self.dump(dump_schema, values.all())

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

        :param filters: dictionary of filters, if not provided it will be created from
            the query_schema
        :param query: additional query parameters, only used when filters
            is not provided
        :param table: sqlalchemy table, if not provided the default :attr:`.db_table` is
            used instead
        :param conn: optional db connection
        """
        table = table if table is not None else self.db_table
        if filters is None:
            filters = self.get_filters(query=query, query_schema=query_schema)
        values = await self.db.db_select(table, filters, conn=conn, consumer=self)
        row = values.first()
        if row is None:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, row)

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
        """Update a single model"""
        table = table if table is not None else self.db_table
        if data is None:
            data = self.cleaned("body_schema", await self.json_data(), strict=False)
        if not filters:
            filters = self.get_filters(query=query, query_schema=query_schema)

        if data:
            try:
                values = await self.db.db_update(
                    table, filters, data, conn=conn, consumer=self
                )
            except IntegrityError as exc:
                self.handle_unique_violation(exc)
                raise
        else:
            values = await self.db.db_select(table, filters, conn=conn, consumer=self)
        row = values.first()
        if row is None:
            raise web.HTTPNotFound()
        return self.dump(dump_schema, row)

    async def delete_one(
        self,
        *,
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        query_schema: SchemaTypeOrStr = "query_schema",
        conn: Optional[Connection] = None,
    ) -> Record:
        """Delete a single model"""
        table = table if table is not None else self.db_table
        if filters is None:
            filters = self.get_filters(query=query, query_schema=query_schema)
        values = await self.db.db_delete(table, filters, conn=conn, consumer=self)
        row = values.first()
        if row is None:
            raise web.HTTPNotFound()
        return row

    async def delete_list(
        self,
        *,
        filters: Optional[StrDict] = None,
        query: Optional[StrDict] = None,
        table: Optional[sa.Table] = None,
        query_schema: SchemaTypeOrStr = "query_schema",
        conn: Optional[Connection] = None,
    ) -> Records:
        """delete multiple models"""
        table = table if table is not None else self.db_table
        # TODO: allow pagination and search
        _, _, filters = self.get_pag_search_filters(
            filters=filters, query=query, query_schema=query_schema
        )
        return await self.db.db_delete(table, filters, conn=conn, consumer=self)

    def handle_unique_violation(self, exception: IntegrityError):
        match = re.search(unique_regex, str(exception))
        if match:
            column = match.group("column")
            message = f"{column} already exists"
            self.raise_validation_error(message=message)
