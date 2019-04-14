import aiohttp

from openapi.testing import jsonBody


async def test_invalid_ws_protocol(cli):
    resp = await cli.get("/stream")
    await jsonBody(resp, 400)


async def test_invalid_protocol(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_str("hkjhkhk")
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["error"]
        assert data["error"]["message"] == "JSON string expected"


async def test_invalid_protocol2(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json([1])
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["error"]
        assert data["error"]["message"] == (
            "Malformed message; expected dictionary, got list"
        )


async def test_invalid_rpc(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(dict(method="echo", payload=dict(message="hello")))
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["error"]
        assert data["error"]["message"] == "Invalid RPC parameters"


async def test_rpc_echo(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(dict(id="abc", method="echo", payload=dict(message="hello")))
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["method"] == "echo"
        assert data["response"] == dict(message="hello")


async def test_invalid_rpc_method(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(dict(id="abc", method="wtf", payload=dict(message="hello")))
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["error"]
        assert data["error"]["message"] == "Invalid RPC parameters"
        assert data["error"]["errors"] == dict(method="wtf method not available")


async def test_rpc_publish_error(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(
            dict(id="abc", method="publish", payload=dict(message="hello"))
        )
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["error"]
        assert data["error"]["message"] == "Invalid RPC parameters"
        assert data["error"]["errors"]["channel"] == "required"


async def test_rpc_publish(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(
            dict(id="abc", method="publish", payload=dict(channel="test", data="hello"))
        )
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["response"] == dict(channel="test", data="hello")


async def test_rpc_subscribe(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(
            dict(id="abc", method="subscribe", payload=dict(channel="test"))
        )
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["response"] == dict(subscribed={"test": ["*"]})
        await ws.send_json(
            dict(id="abcd", method="subscribe", payload=dict(channel="foo"))
        )
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abcd"
        assert data["response"] == dict(subscribed={"test": ["*"], "foo": ["*"]})


async def test_rpc_unsubscribe(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(
            dict(id="abc", method="subscribe", payload=dict(channel="test"))
        )
        await ws.receive()
        await ws.send_json(
            dict(id="abcd", method="subscribe", payload=dict(channel="foo"))
        )
        msg = await ws.receive()
        data = msg.json()
        assert data["response"] == dict(subscribed={"test": ["*"], "foo": ["*"]})
        await ws.send_json(
            dict(id="xyz", method="unsubscribe", payload=dict(channel="test"))
        )
        msg = await ws.receive()
        data = msg.json()
        assert data["response"] == dict(subscribed={"foo": ["*"]})


async def test_rpc_pubsub(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(
            dict(id="abc", method="subscribe", payload=dict(channel="test"))
        )
        await ws.receive()
        await ws.send_json(
            dict(
                id="abc",
                method="publish",
                payload=dict(channel="test", data="hello again"),
            )
        )
        msg = await ws.receive()
        data = msg.json()
        assert data["response"] == dict(channel="test", data="hello again")
        #
        # now receive the message
        msg = await ws.receive()
        data = msg.json()
        assert data["channel"] == "test"
        assert data["data"] == "hello again"


async def test_cancelled(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(dict(id="abc", method="cancel"))
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.CLOSE


async def test_badjson(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(dict(id="abc", method="badjson"))
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["error"]
        assert data["error"]["message"] == "JSON object expected"
