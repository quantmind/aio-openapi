import asyncio


class CannotSubscribe(RuntimeError):
    """Raised by a :class:`.ServiceManager`.

    When a :class:`.ServiceManager` is not able to subscribe to a channel
    it should raise this exception
    """


class ChannelCallbackError(RuntimeError):
    """Exception which allow for a clean callback removal"""


class CannotPublish(RuntimeError):
    """Raised when not possible to publish event into channels"""


CONNECTION_ERRORS = (
    asyncio.CancelledError,
    asyncio.TimeoutError,
    RuntimeError,
    ConnectionResetError,
)
