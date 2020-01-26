from openapi.spec.path import BAD_DATA_MESSAGE
from openapi.testing import jsonBody


async def test_bad_data(cli):
    for bad in ([1], 3, "ciao"):
        response = await cli.post("/tasks", json=bad)
        data = await jsonBody(response, 400)
        assert data["message"] == BAD_DATA_MESSAGE
