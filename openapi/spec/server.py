from typing import Dict, Optional

from .path import full_url


def get_spec(request) -> Optional[Dict]:
    if "spec_doc" in request.app:
        return request.app["spec_doc"].get(request)


def default_server(request):
    app = request.app
    url = full_url(request)
    url = url.with_path(app["cli"].base_path)
    return dict(url=str(url), description="Api server")


def server_urls(request, paths):
    base_path = request.app["cli"].base_path
    n = len(base_path)
    spec = get_spec(request)
    base_url = spec["servers"][0]["url"] if spec else "/"
    return [f"{base_url}{p[n:]}" for p in paths]
