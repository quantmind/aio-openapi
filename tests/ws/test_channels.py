import asyncio
import re

import pytest
from async_timeout import timeout

from openapi.ws.utils import redis_to_py_pattern
from tests.example.ws import LocalBroker


@pytest.fixture
async def channels():
    broker = LocalBroker()
    await broker.start()
    try:
        yield broker.channels
    finally:
        await broker.close()


async def test_channels_properties(channels):
    assert channels.sockets
    await channels.register("foo", "*", lambda c, e, d: d)
    assert len(channels) == 1
    assert "foo" in channels


async def test_channels_wildcard(channels):
    future = asyncio.Future()

    def fire(channel, event, data):
        future.set_result(event)

    await channels.register("test1", "*", fire)
    await channels.sockets.publish("test1", "boom", "ciao!")
    async with timeout(1):
        result = await future
        assert result == "boom"
    assert len(channels) == 1
    await channels.sockets.close()
    assert len(channels) == 0


def test_redis_to_py_pattern():
    p = redis_to_py_pattern("h?llo")
    c = re.compile(p)
    assert match(c, "hello")
    assert match(c, "hallo")
    assert not_match(c, "haallo")
    assert not_match(c, "hallox")
    #
    p = redis_to_py_pattern("h*llo")
    c = re.compile(p)
    assert match(c, "hello")
    assert match(c, "hallo")
    assert match(c, "hasjdbvhckjcvkfcdfllo")
    assert not_match(c, "haallox")
    assert not_match(c, "halloouih")
    #
    p = redis_to_py_pattern("h[ae]llo")
    c = re.compile(p)
    assert match(c, "hello")
    assert match(c, "hallo")
    assert not_match(c, "hollo")


def match(c, text):
    return c.match(text).group() == text


def not_match(c, text):
    return c.match(text) is None
