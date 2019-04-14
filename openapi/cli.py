import asyncio
import os
import sys

import click
import uvloop
from aiohttp import web

from . import spec
from .logger import logger, setup_logging
from .spec.spec import SpecDoc
from .utils import get_debug_flag

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
HOST = os.environ.get("MICRO_SERVICE_HOST", "0.0.0.0")
PORT = os.environ.get("MICRO_SERVICE_PORT", 8080)


class OpenApiClient(click.Group):
    def __init__(
        self,
        spec,
        setup_app=None,
        base_path=None,
        commands=None,
        callback=None,
        **extra,
    ) -> None:
        params = list(extra.pop("params", None) or ())
        self.spec = spec
        self.debug = get_debug_flag()
        self.setup_app = setup_app
        self.base_path = base_path or ""
        params.extend(
            (
                click.Option(
                    ["--version"],
                    help="Show the server version",
                    expose_value=False,
                    callback=self.get_server_version,
                    is_flag=True,
                    is_eager=True,
                ),
                click.Option(
                    ["-v", "--verbose"],
                    help="Increase logging verbosity",
                    is_flag=True,
                    is_eager=True,
                ),
                click.Option(
                    ["-q", "--quiet"],
                    help="Decrease logging verbosity",
                    is_flag=True,
                    is_eager=True,
                ),
            )
        )
        super().__init__(params=params, callback=setup_logging, **extra)
        self.add_command(serve)
        for command in commands or ():
            self.add_command(command)
        self._web = None

    def web(self):
        """Return the web application
        """
        if self._web is None:
            app = web.Application()
            app["cli"] = self
            app["spec"] = self.spec
            app["spec_doc"] = SpecDoc()
            app["cwd"] = os.getcwd()
            spec.setup_app(app)
            if self.setup_app:
                self.setup_app(app)
            self._web = app
        return self._web

    def get_serve_app(self):
        app = self.web()
        if self.base_path:
            base = web.Application()
            base.add_subapp(self.base_path, app)
            base["cli"] = self
            app = base
        return app

    def get_command(self, ctx, name):
        ctx.obj = dict(app=self.web())
        return super().get_command(ctx, name)

    def list_commands(self, ctx):
        ctx.obj = dict(app=self.web())
        return super().list_commands(ctx)

    def get_server_version(self, ctx, param, value):
        if not value or ctx.resilient_parsing:
            return
        spec = self.spec
        message = "%(title)s %(version)s\nPython %(python_version)s"
        click.echo(
            message
            % {
                "title": spec.title,
                "version": spec.version,
                "python_version": sys.version,
            },
            color=ctx.color,
        )
        ctx.exit()


@click.command("serve", short_help="Start aiohttp server.")
@click.option(
    "--host", "-h", default=HOST, help=f"The interface to bind to (default to {HOST})"
)
@click.option(
    "--port", "-p", default=PORT, help=f"The port to bind to (default to {PORT}."
)
@click.option(
    "--reload/--no-reload",
    default=None,
    help="Enable or disable the reloader. By default the reloader "
    "is active if debug is enabled.",
)
@click.pass_context
def serve(ctx, host, port, reload):
    """Run the aiohttp server.
    """
    app = ctx.obj["app"]["cli"].get_serve_app()
    access_log = logger if ctx.obj["log_level"] else None
    web.run_app(app, host=host, port=port, access_log=access_log)
