from .example.db import meta

from openapi.data.db import dataclass_from_table
from openapi.data.fields import VALIDATOR, UUIDValidator


def test_convert_task():
    table = meta().tables['tasks']
    Tasks = dataclass_from_table('Tasks', table)
    assert Tasks


def test_convert_random():
    table = meta().tables['randoms']
    Tasks = dataclass_from_table('Randoms', table)
    assert Tasks
    fields = Tasks.__dataclass_fields__
    assert isinstance(fields['id'].metadata[VALIDATOR], UUIDValidator)
