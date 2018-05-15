import pytest

from click.testing import CliRunner
from openapi.rest import rest
from openapi import db


@pytest.fixture
def app():
    return rest(setup_app=db.setup_app)


def test_db(app):
    runner = CliRunner()
    result = runner.invoke(app, ['db', '--help'])
    assert result.exit_code == 0
    assert result.output.startswith('Usage: root db [OPTIONS]')


def __test_db_init(app):
    runner = CliRunner()
    result = runner.invoke(app, ['db', 'init'])
    assert result.exit_code == 0
    assert result.output.startswith('Usage: root db [OPTIONS]')
