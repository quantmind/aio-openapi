import os
from click.testing import CliRunner


def test_init(cli):
    runner = CliRunner()

    result = runner.invoke(cli.app['cli'], ['db', 'init'])
    assert result.exit_code == 0
    assert os.path.isdir('migrations')
