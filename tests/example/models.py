import enum
from datetime import datetime
from decimal import Decimal

from dataclasses import dataclass

from openapi.data.fields import (
    data_field, date_time_field, enum_field,
    integer_field,
    decimal_field,
)
from openapi.rest import orderable, Query


class TaskType(enum.Enum):
    todo = 0
    issue = 1


@dataclass
class TaskAdd:
    title: str = data_field(required=True)
    severity: int = integer_field()
    type: TaskType = enum_field(TaskType, default=TaskType.todo)
    unique_title: str = data_field()
    story_points: Decimal = decimal_field(default=0.0)

    @classmethod
    def validate(cls, data, errors):
        """here just for coverage
        """


@dataclass
class Task(TaskAdd):
    id: int = data_field(required=True)
    done: datetime = date_time_field()
    story_points: Decimal = decimal_field()


@dataclass
class TaskQuery:
    title: str = data_field()
    done: bool = data_field()
    type: TaskType = enum_field(TaskType)
    severity: int = integer_field(ops=('lt', 'le', 'gt', 'ge', 'ne'))
    story_points: Decimal = decimal_field()


@dataclass
class TaskOrderableQuery(TaskQuery, orderable('title'), Query):
    pass


@dataclass
class TaskUpdate:
    title: str = data_field()
    unique_title: str = data_field()
    severity: int = integer_field()
    story_points: Decimal = decimal_field()
    done: datetime = date_time_field()


@dataclass
class TaskPathSchema:
    id: int = data_field(required=True)


@dataclass
class TaskPathSchema2:
    task_id: int = data_field(required=True)
