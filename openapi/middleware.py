import os

from aiohttp import web

from .exc import ImproperlyConfigured

try:
    from . import sentry
except ImportError:  # pragma: no cover
    sentry = None

ERROR_500 = os.environ.get("ERROR_500_MESSSAGE", "Internal Server Error")


def sentry_middleware(app, dsn, env="dev"):
    if not sentry:  # pragma: no cover
        raise ImproperlyConfigured("Sentry middleware requires sentry-sdk")
    sentry.setup(app, dsn, env)


def json_error(status_codes=None):
    status_codes = set(status_codes or (404, 405, 500))
    content_type = "application/json"

    @web.middleware
    async def json_middleware(request, handler):
        try:
            response = await handler(request)
            if response.status not in status_codes:
                return response
            message = response.message
            status = response.status
        except web.HTTPException as ex:
            if ex.status not in status_codes or ex.content_type == content_type:
                raise
            message = ex.reason
            status = ex.status
            if isinstance(message, str):
                message = {"error": message}
        except Exception:
            if 500 in status_codes:
                status = 500
                message = {"error": ERROR_500}
                request.app.logger.exception(ERROR_500)
            else:
                raise
        return web.json_response(message, status=status)

    return json_middleware


# backward compatibility
json404 = json_error((404,))
