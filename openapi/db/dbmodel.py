from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, cast

from sqlalchemy import Column, Table, func, select
from sqlalchemy.sql import Select, and_, or_
from sqlalchemy.sql.dml import Delete, Insert, Update

from ..db.container import Database
from ..pagination import PaginationVisitor, SearchVisitor
from ..pagination.cursor import cursor_to_python, flip_sign
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
        sql_query = self.get_query(
            table, table.select(), consumer=consumer, params=filters
        )
        async with self.ensure_connection(conn) as conn:
            return await conn.execute(sql_query)

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
        sql_query = self.get_query(
            table,
            table.delete().returning(*table.columns),
            consumer=consumer,
            params=filters,
        )
        async with self.ensure_connection(conn) as conn:
            return await conn.execute(sql_query)

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
        sql_query = self.get_query(
            table, table.select(), consumer=consumer, params=filters
        )
        return await self.db_count_query(sql_query, conn=conn)

    async def db_count_query(
        self,
        sql_query,
        *,
        conn: Optional[Connection] = None,
    ) -> int:
        count_query = select([func.count()]).select_from(sql_query.alias("inner"))
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
            sql_query = self.get_insert(table, data)
            return await conn.execute(sql_query)

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
        else:
            cols = set()
            for record in records:
                cols.update(record)
            new_records = []
            for record in records:
                if len(record) < len(cols):
                    record = record.copy()
                    missing = cols.difference(record)
                    for col in missing:
                        record[col] = None
                new_records.append(record)
            records = new_records
        return table.insert(records).returning(*table.columns)

    def get_query(
        self,
        table: Table,
        sql_query: QueryType,
        *,
        params: Optional[Dict] = None,
        consumer: Any = None,
    ) -> QueryType:
        """Build an SqlAlchemy query

        :param table: sqlalchemy Table
        :param sql_query: sqlalchemy query type
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
            sql_query = cast(Select, sql_query).where(whereclause)
        return sql_query

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

    def order_by(
        self, table: Table, sql_query: QueryType, order_by: Optional[Union[str, List]]
    ) -> QueryType:
        """Apply ordering to a sql_query"""
        if isinstance(order_by, str):
            order_by = (order_by,)
        for name in order_by or ():
            if name.startswith("-"):
                order_by_column = getattr(table.c, name[1:], None)
                if order_by_column is not None:
                    order_by_column = order_by_column.desc()
            else:
                order_by_column = getattr(table.c, name, None)
            if order_by_column is not None:
                sql_query = sql_query.order_by(order_by_column)
        return sql_query

    def search_visitor(self, table: Table, sql_query: Select) -> "DbSearchVisitor":
        return DbSearchVisitor(db=self, table=table, sql_query=sql_query)

    def pagination_visitor(
        self, table: Table, sql_query: Select
    ) -> "DbPaginationVisitor":
        return DbPaginationVisitor(db=self, table=table, sql_query=sql_query)

    def get_search_clause(
        self, table: Table, sql_query: Select, search: str, search_fields: Sequence[str]
    ) -> Select:
        if not search:
            return sql_query

        columns = [getattr(table.c, col) for col in search_fields]
        return sql_query.where(or_(*(col.ilike(f"%{search}%") for col in columns)))


@dataclass
class DbSearchVisitor(SearchVisitor):
    db: CrudDB
    table: Table
    sql_query: Select

    def apply_search(self, search: str, search_fields: Sequence[str]) -> None:
        self.sql_query = self.db.get_search_clause(
            self.table, self.sql_query, search, search_fields
        )


@dataclass
class DbPaginationVisitor(PaginationVisitor):
    db: CrudDB
    table: Table
    sql_query: Select
    initial_sql: Optional[QueryType] = None

    def apply_offset_pagination(
        self,
        limit: int,
        offset: int,
        order_by: Optional[Union[str, List]],
    ) -> None:
        self.initial_sql = self.sql_query
        sql_query = self.db.order_by(self.table, self.sql_query, order_by)
        if offset:
            sql_query = sql_query.offset(offset)
        if limit:
            sql_query = sql_query.limit(limit)
        self.sql_query = sql_query

    def apply_cursor_pagination(
        self, cursor: Sequence[Tuple[str, str]], limit: int, previous: bool
    ) -> None:
        sql_query = self.sql_query
        order_by = []
        for key, value in cursor:
            order_by.append(flip_sign(key) if previous else key)
            sql_query = sql_query.where(self.filter(key, value, previous))
        self.sql_query = self.db.order_by(self.table, sql_query, order_by).limit(
            limit + 1
        )

    async def execute(self, conn: Connection) -> Tuple[Records, Optional[int]]:
        total = None
        if self.initial_sql is not None:
            total = await self.db.db_count_query(self.initial_sql, conn=conn)
        values = await conn.execute(self.sql_query)
        return values, total

    def filter(self, field: str, value: str, previous: bool) -> Column:
        if field.startswith("-"):
            field = field[1:]
            op = "gt" if previous else "le"
        else:
            op = "lt" if previous else "ge"
        column = getattr(self.table.c, field)
        py_value = cursor_to_python(column.type.python_type, value)
        return self.db.default_filter_field(column, op, py_value)
