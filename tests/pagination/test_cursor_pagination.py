from .utils import direction_asc, direction_desc


async def test_direction_asc(cli2, series):
    assert await direction_asc(cli2, series, "/series_cursor")


async def test_direction_desc(cli2, series):
    assert await direction_desc(cli2, series, "/series_cursor")
