from openapi.testing import json_body


async def test_servers(cli):
    response = await cli.get("/")
    await json_body(response)
