from aiohttp.web import HTTPException

from .json import dumps


class OpenApiError(RuntimeError):
    pass


class ImproperlyConfigured(OpenApiError):
    pass


class JsonHttpException(HTTPException):
    def __init__(self, status=None, **kw):
        self.status_code = status or 500
        kw["content_type"] = "application/json"
        super().__init__(**kw)
        reason = self.reason
        if isinstance(reason, str):
            reason = {"message": reason}
        self.text = dumps(reason)
