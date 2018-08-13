from datetime import date, datetime
import typing

from openapi.db.container import Database
from openapi.data.db import dataclass_from_table
from openapi.data.fields import VALIDATOR, UUIDValidator, REQUIRED
from openapi.data.validate import validate
from openapi.data.dump import dump

from .example.db import meta


db = Database()
meta(db.metadata)


def test_convert_task():
    Tasks = dataclass_from_table('Tasks', db.tasks, exclude=('random',))
    assert Tasks
    fields = Tasks.__dataclass_fields__
    assert 'random' not in fields
    props = {}
    fields['title'].metadata[VALIDATOR].openapi(props)
    assert props['maxLength'] == 64
    assert props['minLength'] == 3


def test_convert_random():
    Randoms = dataclass_from_table('Randoms', db.randoms)
    assert Randoms
    fields = Randoms.__dataclass_fields__
    assert isinstance(fields['id'].metadata[VALIDATOR], UUIDValidator)
    d = validate(Randoms, dict(info='jhgjg'))
    assert d.errors['info'] == 'jhgjg not valid'
    d = validate(Randoms, dict(info=dict(a=3, b='test')))
    assert 'info' not in d.errors


def test_validate():
    Tasks = dataclass_from_table('Tasks', db.tasks, exclude=('id',))
    d = validate(Tasks, dict(title='test'))
    assert not d.errors
    d = validate(Tasks, dict(title='te'))
    assert d.errors['title'] == 'Too short'
    d = validate(Tasks, dict(title='t'*100))
    assert d.errors['title'] == 'Too long'
    d = validate(Tasks, dict(title=40))
    assert d.errors['title'] == 'Must be a string'


def test_date():
    Randoms = dataclass_from_table('Randoms', db.randoms)
    d = validate(Randoms, dict(randomdate='jhgjg'))
    assert d.errors['randomdate'] == 'jhgjg not valid format'
    d = validate(Randoms, dict(randomdate=date.today()))
    assert 'randomdate' not in d.errors
    v = dump(Randoms, d.data)
    assert v['randomdate'] == date.today().isoformat()
    v = dump(Randoms, {'randomdate': datetime.now()})
    assert v['randomdate'] == date.today().isoformat()
    v = dump(Randoms, {'randomdate': date.today().isoformat()})
    assert v['randomdate'] == date.today().isoformat()


def test_json_list():
    Randoms = dataclass_from_table('Randoms', db.randoms)
    fields = Randoms.__dataclass_fields__
    assert fields['jsonlist'].type is typing.List
    d = validate(Randoms, dict(jsonlist='jhgjg'))
    assert d.errors['jsonlist'] == 'jhgjg not valid'
    d = validate(Randoms, dict(jsonlist=['bla', 'foo']))
    assert 'jsonlist' not in d.errors


def test_include():
    Randoms = dataclass_from_table('Randoms', db.randoms, include=('price',))
    fields = Randoms.__dataclass_fields__
    assert len(fields) == 1


def test_require():
    Randoms = dataclass_from_table('Randoms', db.randoms, required=False)
    fields = Randoms.__dataclass_fields__
    assert fields
    for field in fields.values():
        assert field.metadata[REQUIRED] is False
