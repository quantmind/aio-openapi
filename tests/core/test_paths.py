from openapi.testing import jsonBody


async def test_servers(cli):
    response = await cli.get("/")
    await jsonBody(response)
