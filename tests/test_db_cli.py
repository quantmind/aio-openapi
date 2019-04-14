import os

from click.testing import CliRunner

from .example.db import extra


def _migrate(cli, name="test", runner=None) -> CliRunner:
    if not runner:
        runner = CliRunner()
        result = runner.invoke(cli.app["cli"], ["db", "init"])
        assert result.exit_code == 0
        assert os.path.isdir("migrations")
        _drop(cli, runner)
    result = runner.invoke(cli.app["cli"], ["db", "migrate", "-m", name])
    assert result.exit_code == 0
    return runner


def _current(cli, runner=None):
    if not runner:
        runner = CliRunner()
    result = runner.invoke(cli.app["cli"], ["db", "current"])
    assert result.exit_code == 0
    print(result.output)
    return result.output.split()[0]


def _drop(cli, runner=None):
    if not runner:
        runner = CliRunner()
    result = runner.invoke(cli.app["cli"], ["db", "drop"])
    assert result.exit_code == 0
    assert result.output == "tables dropped\n"
    result = runner.invoke(cli.app["cli"], ["db", "tables", "--db"])
    assert result.exit_code == 0
    assert result.output == ""


def test_db(cli):
    runner = CliRunner()
    result = runner.invoke(cli.app["cli"], ["db", "--help"])
    assert result.exit_code == 0
    assert result.output.startswith("Usage: root db [OPTIONS]")
    db = cli.app["db"]
    assert repr(db)


def test_createdb(cli):
    runner = CliRunner()
    result = runner.invoke(cli.app["cli"], ["db", "create", "testing-aio-db"])
    assert result.exit_code == 0
    result = runner.invoke(
        cli.app["cli"], ["db", "create", "testing-aio-db", "--force"]
    )
    assert result.exit_code == 0
    assert result.output == "database testing-aio-db created\n"
    result = runner.invoke(cli.app["cli"], ["db", "create", "testing-aio-db"])
    assert result.exit_code == 0
    assert result.output == "database testing-aio-db already available\n"


def test_migration_upgrade(cli):
    runner = _migrate(cli)
    result = runner.invoke(cli.app["cli"], ["db", "upgrade"])
    assert result.exit_code == 0

    # delete column to check if tables will be dropped and recreated
    db = cli.app["db"]
    db.engine.execute("ALTER TABLE tasks DROP COLUMN title")

    result = runner.invoke(cli.app["cli"], ["db", "upgrade", "--drop-tables"])
    assert result.exit_code == 0

    assert "title" in db.metadata.tables["tasks"].c


def test_show_migration(cli):
    runner = _migrate(cli)
    result = runner.invoke(cli.app["cli"], ["db", "show"])
    assert result.exit_code == 0
    assert result.output.split("\n")[4].strip() == "test"


def test_history(cli):
    runner = _migrate(cli)
    result = runner.invoke(cli.app["cli"], ["db", "history"])
    assert result.exit_code == 0
    assert result.output.strip().startswith("<base> -> ")


def test_upgrade(cli):
    runner = _migrate(cli)
    result = runner.invoke(cli.app["cli"], ["db", "upgrade"])
    assert result.exit_code == 0


def test_downgrade(cli):
    runner = _migrate(cli)
    runner.invoke(cli.app["cli"], ["db", "upgrade", "--drop-tables"])
    name = _current(cli, runner)

    extra(cli.app["db"].metadata)
    _migrate(cli, name="extra", runner=runner)

    # upgrade to new migration
    result = runner.invoke(cli.app["cli"], ["db", "upgrade"])
    assert result.exit_code == 0
    name2 = _current(cli, runner)

    assert name != name2

    # downgrade
    result = runner.invoke(cli.app["cli"], ["db", "downgrade", "--revision", name])
    assert result.exit_code == 0
    assert result.output == f"downgraded successfully to {name}\n"
    assert name == _current(cli, runner)


def test_tables(cli):
    runner = CliRunner()
    result = runner.invoke(cli.app["cli"], ["db", "tables"])
    assert result.exit_code == 0
    assert result.output == "\n".join(("multi_key_unique", "randoms", "tasks", ""))


def test_drop(cli):
    _drop(cli)
