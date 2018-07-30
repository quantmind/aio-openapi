import enum
from datetime import datetime

from dataclasses import dataclass

from openapi.data.fields import (
    data_field, date_time_field, decimal_field, enum_field
)


class TaskType(enum.Enum):
    todo = 0
    issue = 1


@dataclass
class TaskAdd:
    title: str = data_field(required=True)
    severity: int = decimal_field()
    type: TaskType = enum_field(TaskType, default=TaskType.todo)

    @classmethod
    def validate(cls, data, errors):
        """here just for coverage
        """


@dataclass
class Task(TaskAdd):
    id: int = data_field(required=True)
    done: datetime = date_time_field()


@dataclass
class TaskQuery:
    done: bool = data_field()
    type: TaskType = enum_field(TaskType)
    severity: int = decimal_field(ops=('lt', 'le', 'gt', 'ge', 'ne'))


@dataclass
class TaskUpdate(TaskAdd):
    done: datetime = date_time_field()


@dataclass
class TaskPathSchema:
    id: int = data_field(required=True)
