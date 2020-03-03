from openapi.data.validate import OBJECT_EXPECTED
from openapi.testing import jsonBody


async def test_bad_data(cli):
    for bad in ([1], 3, "ciao"):
        response = await cli.post("/tasks", json=bad)
        data = await jsonBody(response, 422)
        assert data["message"] == OBJECT_EXPECTED
