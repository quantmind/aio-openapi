import enum

import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from openapi.data import fields
from openapi.db.columns import UUIDColumn

original_init = UUIDType.__init__


class TaskType(enum.Enum):
    todo = 0
    issue = 1


def patch_init(self, binary=True, native=True, **kw):
    original_init(self, binary=binary, native=native)


UUIDType.__init__ = patch_init


def title_field(**kwargs):
    return fields.str_field(**kwargs)


def meta(meta=None):
    """Add task related tables
    """
    if meta is None:
        meta = sa.MetaData()

    sa.Table(
        "tasks",
        meta,
        UUIDColumn("id", make_default=True, doc="Unique ID"),
        sa.Column(
            "title",
            sa.String(64),
            nullable=False,
            info=dict(min_length=3, data_field=title_field),
        ),
        sa.Column("done", sa.DateTime),
        sa.Column("severity", sa.Integer),
        sa.Column("type", sa.Enum(TaskType)),
        sa.Column("unique_title", sa.String, nullable=True, unique=True),
        sa.Column("story_points", sa.Numeric),
        sa.Column("random", sa.String(64)),
    )

    return meta
