import asyncio
import re
from unittest import mock

import pytest

from openapi import ws
from openapi.ws.utils import redis_to_py_pattern


@pytest.fixture
async def channels():
    channels = ws.Channels(ws.LocalBroker(), namespace="test_")
    await channels.start()
    return channels


async def test_channels_properties(channels):
    assert channels.broker
    assert len(channels.status_channel) == 0
    assert channels.status == channels.statusType.initialised
    assert len(channels) == 1
    await channels.register("foo", "*", lambda c, e, d: d)
    assert len(channels) == 2
    assert "foo" in channels
    assert channels.status == channels.statusType.connected


async def test_channels_wildcard(channels):
    future = asyncio.Future()

    def fire(channel, event, data):
        future.set_result(event)

    await channels.register("test1", "*", fire)
    assert channels.status == channels.statusType.connected
    await channels.publish("test1", "boom", "ciao!")
    result = await future
    assert result == "boom"
    assert len(channels) == 2
    await channels.close()
    assert channels.status == channels.statusType.closed


async def test_channels_fail_publish(channels):
    publish = channels.broker.publish
    channels.broker.publish = mock.MagicMock(side_effect=ConnectionRefusedError)
    await channels.publish("channel3", "event2", "failure")
    assert channels.connection_error
    channels.broker.publish = publish
    await channels.publish("channel3", "event2", "failure")
    assert not channels.connection_error


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
