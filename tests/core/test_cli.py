import logging
from unittest.mock import patch

import click
from click.testing import CliRunner

from openapi.logger import logger
from openapi.rest import rest


def test_usage():
    runner = CliRunner()
    result = runner.invoke(rest())
    assert result.exit_code == 0
    assert result.output.startswith("Usage:")


def test_version():
    runner = CliRunner()
    result = runner.invoke(rest(), ["--version"])
    assert result.exit_code == 0
    assert result.output.startswith("Open API")


def test_version_openapi():
    runner = CliRunner()
    result = runner.invoke(
        rest(openapi=dict(title="Test Version", version="1.0")), ["--version"]
    )
    assert result.exit_code == 0
    assert result.output.startswith("Test Version 1.0")


def test_serve():
    runner = CliRunner()
    cli = rest(base_path="/v1")
    with patch("aiohttp.web.run_app") as mock:
        result = runner.invoke(cli, ["--quiet", "serve"])
        assert result.exit_code == 0
        assert mock.call_count == 1
        app = mock.call_args[0][0]
        assert app.router is not None
        assert logger.level == logging.ERROR

    with patch("aiohttp.web.run_app") as mock:
        result = runner.invoke(cli, ["--verbose", "serve"])
        assert result.exit_code == 0
        assert mock.call_count == 1
        app = mock.call_args[0][0]
        assert app.router is not None
        assert logger.level == logging.DEBUG


def test_serve_index():
    runner = CliRunner()
    cli = rest()
    with patch("aiohttp.web.run_app") as mock:
        result = runner.invoke(cli, ["serve", "--index", "1"])
        assert result.exit_code == 0
        assert mock.call_count == 1
        app = mock.call_args[0][0]
        assert app.router is not None
        assert app["index"] == 1
        assert logger.level == logging.INFO


def test_commands():
    runner = CliRunner()
    cli = rest(base_path="/v1", commands=[hello])
    result = runner.invoke(cli, ["hello"])
    assert result.exit_code == 0
    assert result.output.startswith("Hello!")


@click.command("hello")
@click.pass_context
def hello(ctx):
    click.echo("Hello!")
