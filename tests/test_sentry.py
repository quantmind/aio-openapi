import json
import zlib

from openapi.testing import jsonBody


async def test_sentry(cli, sentry_mock, mocker):
    resp = await cli.get("/error")
    await jsonBody(resp, 500)

    calls = [json.loads(zlib.decompress(a[0][1])) for a in sentry_mock.call_args_list]
    assert len(calls) == 1
    assert calls[0]["environment"] == "test"
    middleware_call = calls[0]
    request_info = middleware_call["request"]
    expected_keys = {"cookies", "data", "headers", "method", "query_string", "url"}
    assert set(request_info).issuperset(expected_keys)
