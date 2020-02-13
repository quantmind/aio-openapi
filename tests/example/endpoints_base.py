from aiohttp import web

from openapi.spec.server import server_urls

base_routes = web.RouteTableDef()


@base_routes.get("/")
async def urls(request) -> web.Response:
    paths = set()
    for route in request.app.router.routes():
        route_info = route.get_info()
        path = route_info.get("path", route_info.get("formatter", None))
        paths.add(path)
    return web.json_response(server_urls(request, sorted(paths)))


@base_routes.get("/status")
async def status(request) -> web.Response:
    return web.json_response({})


@base_routes.get("/error")
async def error(request) -> web.Response:
    1 / 0  # noqa
