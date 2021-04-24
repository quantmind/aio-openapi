from openapi.data.validate import OBJECT_EXPECTED
from openapi.testing import json_body


async def test_bad_data(cli):
    for bad in ([1], 3, "ciao"):
        response = await cli.post("/tasks", json=bad)
        data = await json_body(response, 422)
        assert data["message"] == OBJECT_EXPECTED
