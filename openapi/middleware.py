import os

from aiohttp import web

ERROR_500 = os.environ.get("ERROR_500_MESSSAGE", "Internal Server Error")


def json_error(status_codes=None):
    status_codes = set(status_codes or (404, 405, 500))

    @web.middleware
    async def json_middleware(request, handler):
        try:
            response = await handler(request)
            if response.status not in status_codes:
                return response
            message = response.message
            status = response.status
        except web.HTTPException as ex:
            if ex.status not in status_codes:
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
