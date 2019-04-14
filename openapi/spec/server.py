from .path import full_url


def get_spec(request):
    return request.app["spec_doc"].get(request)


def default_server(request):
    app = request.app
    url = full_url(request)
    url = url.with_path(app["cli"].base_path)
    return dict(url=str(url), description="Api server")


def server_urls(request, paths):
    base_path = request.app["cli"].base_path
    n = len(base_path)
    base_url = get_spec(request)["servers"][0]["url"]
    return [f"{base_url}{p[n:]}" for p in paths]
