from aiohttp import web
from dataclasses import dataclass


@dataclass
class Redoc:
    path: str = "/doc"
    favicon_url: str = (
        "https://raw.githubusercontent.com/Redocly/redoc/master/demo/favicon.png"
    )
    redoc_js_url: str = (
        "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
    )
    font: str = "family=Montserrat:300,400,700|Roboto:300,400,700"

    def __call__(self, request: web.Request) -> web.Response:
        spec = self.request.app["spec"]
        base_path = "/".join(self.request.path.split("/")[:-1])
        title = spec.info.title
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <title>{title}</title>
        <!-- needed for adaptive design -->
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        """
        if self.font:
            html += f"""
        <link href="https://fonts.googleapis.com/css?{self.font}" rel="stylesheet">
        """
        html += f"""
        <link rel="shortcut icon" href="{self.favicon}">
        <!--
        ReDoc doesn't change outer page styles
        -->
        <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        </style>
        </head>
        <body>
        <redoc spec-url="{base_path}/spec"></redoc>
        <script src="{self.redoc_js_url}"> </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")
