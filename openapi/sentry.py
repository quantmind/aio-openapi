import logging

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def setup(app, dsn, env="dev", level=logging.ERROR, event_level=logging.ERROR):

    sentry_sdk.init(
        dsn=dsn,
        environment=env,
        integrations=[
            LoggingIntegration(
                level=level,  # Capture level and above as breadcrumbs
                event_level=event_level,  # Send event_level and above as events
            ),
            AioHttpIntegration(),
        ],
    )
