from dataclasses import dataclass
from typing import List

from aiohttp import web

from openapi.data.db import dataclass_from_table
from openapi.db.path import SqlApiPath
from openapi.pagination import cursorPagination
from openapi.spec import op

from .db import DB

series_routes = web.RouteTableDef()


Serie = dataclass_from_table(
    "Serie", DB.series, required=True, default=True, exclude=("group",)
)


@dataclass
class SeriesQuery(
    dataclass_from_table(
        "_SeriesQuery",
        DB.series,
        default=True,
        include=("group", "date"),
        ops=dict(date=("le", "ge", "gt", "lt")),
    ),
    cursorPagination("-date"),
):
    """Series query with cursor pagination"""


@series_routes.view("/series")
class SeriesPath(SqlApiPath):
    """
    ---
    summary: Get Series
    tags:
        - Series
    """

    table = "series"

    @op(query_schema=SeriesQuery, response_schema=List[Serie])
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
