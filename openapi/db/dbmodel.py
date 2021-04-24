from typing import Any, Dict, List, Optional, Union, cast

from sqlalchemy import Column, Table, func, select
from sqlalchemy.sql import Select, and_
from sqlalchemy.sql.dml import Delete, Insert, Update

from ..db.container import Database
from ..types import Connection, Record, Records

QueryType = Union[Delete, Update, Select]


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
        async with self.ensure_connection(conn) as conn:
            return await conn.execute(query)

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
        async with self.ensure_connection(conn) as conn:
            return await conn.execute(query)

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
        return await self.db_count_query(query, conn=conn)

    async def db_count_query(self, query, *, conn: Optional[Connection] = None) -> int:
        count_query = select([func.count()]).select_from(query.alias("inner"))
        async with self.ensure_connection(conn) as conn:
            result = await conn.execute(count_query)
            return result.scalar()

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
            query = self.get_insert(table, data)
            return await conn.execute(query)

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
            cast(
                Update,
                self.get_query(
                    table, table.update(), consumer=consumer, params=filters
                ),
            )
            .values(**data)
            .returning(*table.columns)
        )
        async with self.ensure_connection(conn) as conn:
            return await conn.execute(update)

    async def db_upsert(
        self,
        table: Table,
        filters: Dict,
        data: Optional[Dict] = None,
        *,
        conn: Optional[Connection] = None,
        consumer: Any = None,
    ) -> Record:
        """Perform an upsert for a single record

        :param table: sqlalchemy Table
        :param filters: key-value pairs for filtering rows to update
        :param data: key-value pairs for updating columns values of selected rows
        :param conn: optional db connection
        :param consumer: optional consumer (see :meth:`.get_query`)
        """
        if data:
            result = await self.db_update(
                table, filters, data, conn=conn, consumer=consumer
            )
        else:
            result = await self.db_select(table, filters, conn=conn, consumer=consumer)
        record = result.one_or_none()
        if record is None:
            insert_data = data.copy() if data else {}
            insert_data.update(filters)
            result = await self.db_insert(table, insert_data, conn=conn)
            record = result.one()
        return record

    def get_insert(self, table: Table, records: Union[List[Dict], Dict]) -> Insert:
        if isinstance(records, dict):
            records = [records]
        return table.insert(records).returning(*table.columns)

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
