import os
import sys
import asyncio

from aiohttp import web
import click
import dotenv
import uvloop

from .utils import get_debug_flag
from . import spec


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class OpenApiClient(click.Group):

    def __init__(self, spec, setup_app=None, **extra):
        params = list(extra.pop('params', None) or ())
        self.spec = spec
        self.debug = get_debug_flag()
        self.setup_app = setup_app
        params.extend(
            (
                click.Option(
                    ['--version'],
                    help='Show the server version',
                    expose_value=False,
                    callback=self.get_server_version,
                    is_flag=True,
                    is_eager=True
                ),
            )
        )
        super().__init__(params=params, **extra)
        self.add_command(serve)
        self._web = None

    def web(self):
        """Return the web application
        """
        if self._web is None:
            app = web.Application(
                debug=get_debug_flag()
            )
            app['cli'] = self
            app['spec'] = self.spec
            app['cwd'] = os.getcwd()
            spec.setup_app(app)
            if self.setup_app:
                self.setup_app(app)
            self._web = app
        return self._web

    def get_command(self, ctx, name):
        ctx.app = self.web()
        return super().get_command(ctx, name)

    def list_commands(self, ctx):
        ctx.app = self.web()
        return super().list_commands(ctx)

    def main(self, *args, **kwargs):
        os.environ['OPENAPI_RUN_FROM_CLI'] = 'true'
        self.load_dotenv()
        return super().main(*args, **kwargs)

    def load_dotenv(self, path=None):
        if path is not None:
            return dotenv.load_dotenv(path)
        path = dotenv.find_dotenv('.env', usecwd=True)
        if path:
            dotenv.load_dotenv(path)

    def get_server_version(self, ctx, param, value):
        if not value or ctx.resilient_parsing:
            return
        spec = self.spec
        message = '%(title)s %(version)s\nPython %(python_version)s'
        click.echo(message % {
            'title': spec.title,
            'version': spec.version,
            'python_version': sys.version,
        }, color=ctx.color)
        ctx.exit()

    def _load_plugin_commands(self):
        if self._loaded_plugin_commands:
            return
        try:
            import pkg_resources
        except ImportError:
            self._loaded_plugin_commands = True
            return

        for ep in pkg_resources.iter_entry_points('openapi.commands'):
            self.add_command(ep.load(), ep.name)
        self._loaded_plugin_commands = True


@click.command('serve', short_help='Start aiohttp server.')
@click.option('--host', '-h', default='127.0.0.1',
              help='The interface to bind to.')
@click.option('--port', '-p', default=8080,
              help='The port to bind to.')
@click.option('--reload/--no-reload', default=None,
              help='Enable or disable the reloader. By default the reloader '
              'is active if debug is enabled.')
@click.pass_context
def serve(ctx, host, port, reload):
    """Run the aiohttp server.
    """
    app = ctx.parent.app
    if reload is None and app.debug:
        reload = True

    def inner():
        web.run_app(app, host=host, port=port)

    inner()
