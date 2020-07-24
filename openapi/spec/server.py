from typing import Dict, List

from aiohttp import web

from .path import full_url


def default_server(request: web.Request) -> Dict[str, str]:
    app = request.app
    url = full_url(request)
    url = url.with_path(app["cli"].base_path)
    return dict(url=str(url), description="Api server")


def server_urls(request: web.Request, paths: List[str]) -> List[str]:
    base_path = request.app["cli"].base_path
    n = len(base_path)
    spec = request.app.get("spec")
    server = spec.servers[0] if spec and spec.servers else default_server(request)
    base_url = server["url"]
    return [f"{base_url}{p[n:]}" for p in paths]
