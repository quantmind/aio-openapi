from dataclasses import dataclass
from typing import List

from aiohttp import web

from openapi.data.db import dataclass_from_table
from openapi.db.path import SqlApiPath
from openapi.pagination import cursorPagination, offsetPagination
from openapi.spec import op

from .db import DB

series_routes = web.RouteTableDef()


Serie = dataclass_from_table(
    "Serie", DB.series, required=True, default=True, exclude=("group",)
)


BaseQuery = dataclass_from_table(
    "BaseQuery",
    DB.series,
    default=True,
    include=("group", "date"),
    ops=dict(date=("le", "ge", "gt", "lt")),
)


@dataclass
class SeriesQueryCursor(
    BaseQuery,
    cursorPagination("-date"),
):
    """Series query with cursor pagination"""


@dataclass
class SeriesQueryOffset(
    BaseQuery,
    offsetPagination("-date", "date"),
):
    """Series query with offset pagination"""


@series_routes.view("/series_cursor")
class SeriesPath(SqlApiPath):
    """
    ---
    summary: Get Series
    tags:
        - Series
    """

    table = "series"

    @op(query_schema=SeriesQueryCursor, response_schema=List[Serie])
    async def get(self):
        """
        ---
        summary: Retrieve Series
        description: Retrieve a TimeSeries
        responses:
            200:
                description: timeseries
        """
        paginated = await self.get_list()
        return paginated.json_response()


@series_routes.view("/series_offset")
class SeriesOffsetPath(SqlApiPath):
    """
    ---
    summary: Get Series
    tags:
        - Series
    """

    table = "series"

    @op(query_schema=SeriesQueryOffset, response_schema=List[Serie])
    async def get(self):
        """
        ---
        summary: Retrieve Series
        description: Retrieve a TimeSeries
        responses:
            200:
                description: timeseries
        """
        paginated = await self.get_list()
        return paginated.json_response()
