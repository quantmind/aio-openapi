import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from openapi.data import fields
from openapi.rest import Query, orderable, searchable


class TaskType(enum.Enum):
    todo = 0
    issue = 1


@dataclass
class TaskAdd:
    title: str = fields.str_field(required=True, description="Task title")
    severity: int = fields.integer_field(description="Task severity")
    type: TaskType = fields.enum_field(
        TaskType, default=TaskType.todo, description="Task type"
    )
    unique_title: str = fields.str_field(description="Unique title of the Task")
    story_points: Decimal = fields.decimal_field(
        default=0.0, description="Task story points"
    )

    @classmethod
    def validate(cls, data, errors):
        """here just for coverage
        """


@dataclass
class Task(TaskAdd):
    id: str = fields.uuid_field(required=True, description="Task ID")
    done: datetime = fields.date_time_field(description="Done timestamp")
    story_points: Decimal = fields.decimal_field(description="Story points")


@dataclass
class TaskQuery(Query):
    title: str = fields.str_field(description="Task title")
    done: bool = fields.str_field(description="Done timestamp")
    type: TaskType = fields.enum_field(TaskType, description="Task type")
    severity: int = fields.integer_field(
        ops=("lt", "le", "gt", "ge", "ne"), description="Task severity"
    )
    story_points: Decimal = fields.decimal_field(description="Story points")


@dataclass
class TaskOrderableQuery(
    TaskQuery, orderable("title"), searchable("title", "unique_title")
):
    pass


@dataclass
class TaskUpdate(TaskAdd):
    done: datetime = fields.date_time_field(description="Done timestamp")


@dataclass
class TaskPathSchema:
    id: str = fields.uuid_field(required=True, description="Task ID")


@dataclass
class TaskPathSchema2:
    task_id: str = fields.uuid_field(required=True, description="Task ID")


@dataclass
class MultiKey:
    x: int
    y: int


@dataclass
class Permission:
    paths: List[str] = fields.data_field(description="Permition paths")
    methods: List[str] = fields.data_field(description="Permition methods")
    body: Dict[str, str] = fields.json_field(description="Permission body")
    action: str = fields.str_field(default="allow", description="Permition action")


@dataclass
class Role:
    name: str = fields.str_field(required=True, description="Role name")
    permissions: List[Permission] = fields.data_field(
        required=True, description="List of permissions"
    )


@dataclass
class Moon:
    names: str = fields.str_field(
        description="Comma separated list of names",
        post_process=lambda values: [v.strip() for v in values.split(",")],
    )
