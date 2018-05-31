import asyncio

import pytest


@pytest.fixture(autouse=True)
def loop():
    return asyncio.get_event_loop()
