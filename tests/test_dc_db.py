import typing
from datetime import date, datetime

from openapi.data.db import dataclass_from_table
from openapi.data.dump import dump
from openapi.data.fields import REQUIRED, VALIDATOR, UUIDValidator, field_dict
from openapi.data.validate import validate


def test_convert_task(db):
    Tasks = dataclass_from_table("Tasks", db.tasks, exclude=("random",))
    assert Tasks
    fields = field_dict(Tasks)
    assert "random" not in fields
    props = {}
    fields["title"].metadata[VALIDATOR].openapi(props)
    assert props["maxLength"] == 64
    assert props["minLength"] == 3


def test_convert_random(db):
    Randoms = dataclass_from_table("Randoms", db.randoms)
    assert Randoms
    fields = field_dict(Randoms)
    assert isinstance(fields["id"].metadata[VALIDATOR], UUIDValidator)
    d = validate(Randoms, dict(info="jhgjg"))
    assert d.errors["info"] == "expected an object"
    d = validate(Randoms, dict(info=dict(a="3", b="test")))
    assert not d.errors


def test_validate(db):
    Tasks = dataclass_from_table("Tasks", db.tasks, exclude=("id",))
    d = validate(Tasks, dict(title="test"))
    assert not d.errors
    d = validate(Tasks, dict(title="te"))
    assert d.errors["title"] == "Too short"
    d = validate(Tasks, dict(title="t" * 100))
    assert d.errors["title"] == "Too long"
    d = validate(Tasks, dict(title=40))
    assert d.errors["title"] == "Must be a string"


def test_date(db):
    Randoms = dataclass_from_table("Randoms", db.randoms)
    d = validate(Randoms, dict(randomdate="jhgjg"))
    assert d.errors["randomdate"] == "jhgjg not valid format"
    d = validate(Randoms, dict(randomdate=date.today()))
    assert not d.errors
    v = dump(Randoms, d.data)
    assert v["randomdate"] == date.today().isoformat()
    v = dump(Randoms, {"randomdate": datetime.now()})
    assert v["randomdate"] == date.today().isoformat()
    v = dump(Randoms, {"randomdate": date.today().isoformat()})
    assert v["randomdate"] == date.today().isoformat()


def test_json_list(db):
    Randoms = dataclass_from_table("Randoms", db.randoms)
    fields = field_dict(Randoms)
    assert fields["jsonlist"].type is typing.List
    d = validate(Randoms, dict(jsonlist="jhgjg"))
    assert d.errors["jsonlist"] == "expected a sequence"
    d = validate(Randoms, dict(jsonlist=["bla", "foo"]))
    assert not d.errors


def test_include(db):
    Randoms = dataclass_from_table("Randoms", db.randoms, include=("price",))
    fields = field_dict(Randoms)
    assert len(fields) == 1


def test_require(db):
    Randoms = dataclass_from_table("Randoms", db.randoms, required=False)
    fields = field_dict(Randoms)
    assert fields
    for field in fields.values():
        assert field.metadata[REQUIRED] is False
