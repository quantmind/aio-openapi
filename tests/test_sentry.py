import zlib
import json

from asynctest import CoroutineMock


async def test_sentry(cli, sentry, mocker):
    mock = CoroutineMock()
    mocker.patch(
        'raven_aiohttp.AioHttpTransport._do_send', mock
    )
    resp = await cli.get('/error')
    assert resp.status == 500

    try:
        raise ValueError()
    except ValueError:
        sentry.captureException()

    calls = [json.loads(zlib.decompress(a[0][1])) for a in mock.call_args_list]
    assert len(calls) == 2
    assert calls[0]['environment'] == calls[1]['environment'] == 'dad'
    middleware_call = calls[0]
    request_info = middleware_call['request']
    expected_keys = {
        'cookies', 'data', 'headers', 'method', 'query_string', 'url',
    }
    assert set(request_info).issuperset(expected_keys)
