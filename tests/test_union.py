from openapi.testing import json_body


async def test_multicolumn_union(cli):
    row = {"x": 1, "y": 2}
    resp = await cli.post("/multikey", json=row)
    assert await json_body(resp, status=201) == row
    row2 = {"x": "ciao", "y": 2}
    resp = await cli.post("/multikey", json=row2)
    assert await json_body(resp, status=201) == row2
