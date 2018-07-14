import sqlalchemy as sa

from .models import TaskType


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
        sa.Column('type', sa.Enum(TaskType))
    )

    return meta
