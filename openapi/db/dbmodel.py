from typing import Any, Dict, List, Optional, Union, cast

from asyncpg import Connection
from sqlalchemy import Column, Table
from sqlalchemy.sql import and_

from ..db.container import Database
from ..types import Records
from .compile import QueryType, Select, compile_query, count


class CrudDB(Database):
    """A :class:`.Database` with additional methods for CRUD operations"""

    async def db_select(
        self,
        table: Table,
        filters: Dict,
        *,
        conn: Optional[Connection] = None,
        consumer: Any = None,
    ) -> Records:
        """Select rows from a given table

        :param table: sqlalchemy Table
        :param filters: key-value pairs for filtering rows
        :param conn: optional db connection
        :param consumer: optional consumer (see :meth:`.get_query`)
        """
        query = self.get_query(table, table.select(), consumer=consumer, params=filters)
        sql, args = compile_query(query)
        async with self.ensure_connection(conn) as conn:
            return await conn.fetch(sql, *args)

    async def db_delete(
        self,
        table: Table,
        filters: Dict,
        *,
        conn: Optional[Connection] = None,
        consumer: Any = None,
    ) -> Records:
        """Delete rows from a given table

        :param table: sqlalchemy Table
        :param filters: key-value pairs for filtering rows
        :param conn: optional db connection
        :param consumer: optional consumer (see :meth:`.get_query`)
        """
        query = self.get_query(
            table,
            table.delete().returning(*table.columns),
            consumer=consumer,
            params=filters,
        )
        sql, args = compile_query(query)
        async with self.ensure_connection(conn) as conn:
            return await conn.fetch(sql, *args)

    async def db_count(
        self,
        table: Table,
        filters: Dict,
        *,
        conn: Optional[Connection] = None,
        consumer: Any = None,
    ) -> int:
        """Count rows in a table

        :param table: sqlalchemy Table
        :param filters: key-value pairs for filtering rows
        :param conn: optional db connection
        :param consumer: optional consumer (see :meth:`.get_query`)
        """
        query = self.get_query(table, table.select(), consumer=consumer, params=filters)
        sql, args = count(cast(Select, query))
        async with self.ensure_connection(conn) as conn:
            total = await conn.fetchrow(sql, *args)
        return total[0]

    async def db_insert(
        self,
        table: Table,
        data: Union[List[Dict], Dict],
        *,
        conn: Optional[Connection] = None,
    ) -> Records:
        """Perform an insert into a table

        :param table: sqlalchemy Table
        :param data: key-value pairs for columns values
        :param conn: optional db connection
        """
        async with self.ensure_connection(conn) as conn:
            statement, args = self.get_insert(table, data)
            return await conn.fetch(statement, *args)

    async def db_update(
        self,
        table: Table,
        filters: Dict,
        data: Dict,
        *,
        conn: Optional[Connection] = None,
        consumer: Any = None,
    ) -> Records:
        """Perform an update of rows

        :param table: sqlalchemy Table
        :param filters: key-value pairs for filtering rows to update
        :param data: key-value pairs for updating columns values of selected rows
        :param conn: optional db connection
        :param consumer: optional consumer (see :meth:`.get_query`)
        """
        update = (
            self.get_query(table, table.update(), consumer=consumer, params=filters)
            .values(**data)
            .returning(*table.columns)
        )
        sql, args = compile_query(update)
        async with self.ensure_connection(conn) as conn:
            return await conn.fetch(sql, *args)

    def get_insert(self, table: Table, records: Union[List[Dict], Dict]):
        if isinstance(records, dict):
            records = [records]
        exp = table.insert(records).returning(*table.columns)
        return compile_query(exp)

    def get_query(
        self,
        table: Table,
        query: QueryType,
        *,
        params: Optional[Dict] = None,
        consumer: Any = None,
    ) -> QueryType:
        """Build an SqlAlchemy query

        :param table: sqlalchemy Table
        :param query: sqlalchemy query type
        :param params: key-value pairs for the query
        :param consumer: optional consumer for manipulating parameters
        """
        filters: List = []
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
            whereclause = and_(*filters) if len(filters) > 1 else filters[0]
            query = cast(Select, query).where(whereclause)
        return query

    def default_filter_field(self, field: Column, op: str, value: Any):
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
