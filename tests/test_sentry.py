async def test_sentry(cli, sentry, mocker):
    send_mock = mocker.patch('raven_aiohttp.AioHttpTransport._do_send')
    resp = await cli.get('/error')
    assert resp.status == 500
    send_mock.assert_called_once()
