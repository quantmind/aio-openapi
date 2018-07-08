import os
import sys
import asyncio

from aiohttp import web
import click
import dotenv
import uvloop

from .utils import get_debug_flag, getLogger
from . import spec


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
HOST = os.environ.get('MICRO_SERVICE_HOST', '0.0.0.0')
PORT = os.environ.get('MICRO_SERVICE_PORT', 8080)


class OpenApiClient(click.Group):

    def __init__(self, spec, setup_app=None, base_path=None,
                 commands=None, **extra) -> None:
        params = list(extra.pop('params', None) or ())
        self.spec = spec
        self.debug = get_debug_flag()
        self.setup_app = setup_app
        self.base_path = base_path
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
        for command in commands or ():
            self.add_command(command)
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

    def get_serve_app(self):
        app = self.web()
        if self.base_path:
            base = web.Application(
                debug=get_debug_flag()
            )
            base.add_subapp(self.base_path, app)
            app = base
        return app

    def get_command(self, ctx, name):
        ctx.obj = dict(app=self.web())
        return super().get_command(ctx, name)

    def list_commands(self, ctx):
        ctx.obj = dict(app=self.web())
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


@click.command('serve', short_help='Start aiohttp server.')
@click.option('--host', '-h', default=HOST,
              help=f'The interface to bind to (default to {HOST})')
@click.option('--port', '-p', default=PORT,
              help=f'The port to bind to (default to {PORT}.')
@click.option('--reload/--no-reload', default=None,
              help='Enable or disable the reloader. By default the reloader '
              'is active if debug is enabled.')
@click.pass_context
def serve(ctx, host, port, reload):
    """Run the aiohttp server.
    """
    app = ctx.obj['app']['cli'].get_serve_app()
    if reload is None and app.debug:
        reload = True
    access_log = getLogger()
    web.run_app(app, host=host, port=port, access_log=access_log)
