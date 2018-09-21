import uuid
from datetime import datetime, date

import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from openapi.db.columns import UUIDColumn
from openapi.data import fields

from .models import TaskType

original_init = UUIDType.__init__


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
        'tasks', meta,
        UUIDColumn(
            'id', make_default=True, doc='Unique ID'),
        sa.Column(
            'title', sa.String(64), nullable=False,
            info=dict(min_length=3, data_field=title_field)
        ),
        sa.Column('done', sa.DateTime),
        sa.Column('severity', sa.Integer),
        sa.Column('type', sa.Enum(TaskType)),
        sa.Column('unique_title', sa.String, nullable=True, unique=True),
        sa.Column('story_points', sa.Numeric(2)),
        sa.Column('random', sa.String(64))
    )

    sa.Table(
        'randoms', meta,
        sa.Column(
            'id',
            UUIDType(),
            primary_key=True,
            nullable=False,
            default=uuid.uuid4
        ),
        sa.Column('randomdate', sa.Date, nullable=False, default=date.today),
        sa.Column('timestamp', sa.DateTime, nullable=False,
                  default=datetime.now),
        sa.Column('price', sa.Numeric(precision=100, scale=4), nullable=False),
        sa.Column('tenor', sa.String(3), nullable=False),
        sa.Column('tick', sa.Boolean),
        sa.Column('info', sa.JSON),
        sa.Column('jsonlist', sa.JSON, default=[]),
        sa.Column('task_id', sa.ForeignKey('tasks.id', ondelete='CASCADE'),
                  nullable=False)
    )

    return meta
