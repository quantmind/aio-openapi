from click.testing import CliRunner

from openapi.rest import rest


def test_usage():
    runner = CliRunner()
    result = runner.invoke(rest())
    assert result.exit_code == 0
    assert result.output.startswith('Usage:')


def test_version():
    runner = CliRunner()
    result = runner.invoke(rest(), ['--version'])
    assert result.exit_code == 0
    assert result.output.startswith('Open API')
