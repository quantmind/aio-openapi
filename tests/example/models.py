from datetime import datetime
from dataclasses import dataclass

from openapi.data.fields import (
    data_field, date_time_field
)


@dataclass
class TaskAdd:
    title: str = data_field(required=True)


@dataclass
class Task(TaskAdd):
    done: datetime = date_time_field()


@dataclass
class TaskQuery:
    done: bool = data_field()
