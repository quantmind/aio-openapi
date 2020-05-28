from typing import Dict

from aiohttp import web

from openapi.spec import op
from openapi.spec.path import ApiPath

from .models import BundleUpload

form_routes = web.RouteTableDef()


@form_routes.view("/upload")
class UploadPath(ApiPath):
    """
    ---
    summary: Bulk manage tasks
    tags:
        - Task
    """

    table = "tasks"

    @op(body_schema=BundleUpload, response_schema=Dict)
    async def post(self):
        """
        ---
        summary: Upload a bundle
        description: Upload a bundle
        body_content: multipart/form-data
        responses:
            201:
                description: Created tasks
        """
        return self.json_response(dict(ok=True), status=201)
