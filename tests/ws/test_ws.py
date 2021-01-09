from typing import Dict

import aiohttp
from async_timeout import timeout

from openapi.testing import jsonBody


async def server_info(ws) -> Dict:
    await ws.send_json(dict(id="abc", method="server_info"))
    msg = await ws.receive()
    assert msg.type == aiohttp.WSMsgType.TEXT
    data = msg.json()
    return data["response"]


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
        #
        # test internals
        sockets = cli.app["web_sockets"]
        assert len(sockets.sockets) == 1
        ws = tuple(sockets.sockets)[0]
        assert str(ws) == ws.socket_id


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
        await ws.send_json(
            dict(id="abc", method="publish", payload=dict(channel="Test", data="hello"))
        )
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["error"]
        assert data["error"]["message"] == "Invalid RPC parameters"
        assert data["error"]["errors"]["channel"] == "Cannot publish to channel"


async def test_rpc_publish(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(
            dict(id="abc", method="publish", payload=dict(channel="test", data="hello"))
        )
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        assert data["id"] == "abc"
        assert data["response"] == dict(channel="test", data="hello", event=None)


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
        #
        # server info
        await ws.send_json(dict(id="abc", method="server_info"))
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        response = data["response"]
        assert response["connections"] == 1
        assert len(response["channels"]) == 2
        #
        # invalid channel
        await ws.send_json(
            dict(id="abc", method="subscribe", payload=dict(channel="Test"))
        )
        msg = await ws.receive()
        data = msg.json()
        assert data["error"]["message"] == "Invalid RPC parameters"
        assert data["error"]["errors"]["channel"] == "Invalid channel"


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
        #
        # server info
        await ws.send_json(dict(id="abc", method="server_info"))
        msg = await ws.receive()
        assert msg.type == aiohttp.WSMsgType.TEXT
        data = msg.json()
        response = data["response"]
        assert response["connections"] == 1
        assert len(response["channels"]) == 1


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
        assert data["response"] == dict(channel="test", data="hello again", event=None)
        #
        # now receive the message
        msg = await ws.receive()
        data = msg.json()
        assert data["channel"] == "test"
        assert data["data"] == "hello again"
        #
        await ws.send_json(
            dict(
                id="abc",
                method="publish",
                payload=dict(channel="test", data="error"),
            )
        )
        msg = await ws.receive()
        data = msg.json()
        assert data["response"] == dict(channel="test", data="error", event=None)
        # now receive the message
        async with timeout(2):
            msg = await ws.receive()
            assert msg.type == aiohttp.WSMsgType.CLOSE

    async with cli.ws_connect("/stream") as ws:
        info = await server_info(ws)
        assert info["connections"] == 1
        assert info["channels"] == {}
        #
        await ws.send_json(
            dict(id="abc", method="subscribe", payload=dict(channel="test"))
        )
        await ws.receive()
        #
        await ws.send_json(
            dict(
                id="abc",
                method="publish",
                payload=dict(channel="test", data="runtime_error"),
            )
        )
        msg = await ws.receive()
        data = msg.json()
        assert data["response"] == dict(
            channel="test", data="runtime_error", event=None
        )
        # now receive the message
        async with timeout(2):
            msg = await ws.receive()
            assert msg.type == aiohttp.WSMsgType.CLOSE


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


async def test_rpc_unsubscribe_error(cli):
    async with cli.ws_connect("/stream") as ws:
        await ws.send_json(
            dict(id="xyz", method="unsubscribe", payload=dict(channel="whazaaa"))
        )
        msg = await ws.receive()
        data = msg.json()
        assert data["error"]["message"] == "Invalid RPC parameters"
        assert data["error"]["errors"]["channel"] == "Invalid channel"
