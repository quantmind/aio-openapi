import pytest


async def test_get_attr(cli):
    db = cli.app['db']
    assert db.tasks is db.metadata.tables['tasks']
    with pytest.raises(AttributeError) as ex_info:
        db.fooooo
    assert 'fooooo' in str(ex_info.value)
