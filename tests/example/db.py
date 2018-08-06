from datetime import datetime
import sqlalchemy as sa
import uuid

from sqlalchemy_utils import UUIDType

from .models import TaskType


original_init = UUIDType.__init__


def patch_init(self, binary=True, native=True, **kw):
    original_init(self, binary=binary, native=native)


UUIDType.__init__ = patch_init


def meta(meta=None):
    """Add task related tables
    """
    if meta is None:
        meta = sa.MetaData()

    sa.Table(
        'tasks', meta,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String, nullable=False),
        sa.Column('done', sa.DateTime),
        sa.Column('severity', sa.Integer),
        sa.Column('type', sa.Enum(TaskType)),
        sa.Column('unique_title', sa.String, nullable=True, unique=True),
        sa.Column('story_points', sa.Numeric(2))
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
        sa.Column('timestamp', sa.DateTime, nullable=False,
                  default=datetime.now),
        sa.Column('price', sa.Numeric(precision=100, scale=4), nullable=False),
        sa.Column('tenor', sa.String(3), nullable=False),
        sa.Column('task_id', sa.ForeignKey('tasks.id', ondelete='CASCADE'),
                  nullable=False)
    )

    return meta
