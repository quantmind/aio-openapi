from openapi_spec_validator import validate_spec
from openapi.testing import json_body


async def test_validate_spec(cli) -> None:
    response = await cli.get("/spec")
    spec = await json_body(response)
    validate_spec(spec)
