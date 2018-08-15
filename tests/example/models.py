import enum
from datetime import datetime
from decimal import Decimal

from dataclasses import dataclass

from openapi.data.fields import (
    data_field, date_time_field, decimal_field, enum_field, integer_field,
    uuid_field,
)
from openapi.rest import Query, orderable


class TaskType(enum.Enum):
    todo = 0
    issue = 1


@dataclass
class TaskAdd:
    title: str = data_field(
        required=True, description='Task title'
    )
    severity: int = integer_field(description='Task severity')
    type: TaskType = enum_field(
        TaskType, default=TaskType.todo, description='Task type'
    )
    unique_title: str = data_field(description='Unique title of the Task')
    story_points: Decimal = decimal_field(
        default=0.0, description='Task story points'
    )

    @classmethod
    def validate(cls, data, errors):
        """here just for coverage
        """


@dataclass
class Task(TaskAdd):
    id: str = uuid_field(required=True, description='Task ID')
    done: datetime = date_time_field(description='Done timestamp')
    story_points: Decimal = decimal_field(description='Story points')


@dataclass
class TaskQuery:
    title: str = data_field(description='Task title')
    done: bool = data_field(description='Done timestamp')
    type: TaskType = enum_field(TaskType, description='Task type')
    severity: int = integer_field(
        ops=('lt', 'le', 'gt', 'ge', 'ne'), description='Task severity'
    )
    story_points: Decimal = decimal_field(description='Story points')


@dataclass
class TaskOrderableQuery(TaskQuery, orderable('title'), Query):
    pass


@dataclass
class TaskUpdate(TaskAdd):
    done: datetime = date_time_field(description='Done timestamp')


@dataclass
class TaskPathSchema:
    id: str = uuid_field(required=True, description='Task ID')


@dataclass
class TaskPathSchema2:
    task_id: str = uuid_field(required=True, description='Task ID')
