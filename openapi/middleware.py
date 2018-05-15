from aiohttp import web


@web.middleware
async def json404(request, handler):
    try:
        response = await handler(request)
        if response.status != 404:
            return response
        message = response.message
    except web.HTTPException as ex:
        if ex.status != 404:
            raise
        message = ex.reason
        if isinstance(message, str):
            message = {'error': message}
    return web.json_response(message, status=404)
