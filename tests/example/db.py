import sqlalchemy as sa


def meta(meta=None):
    """Add task related tables
    """
    if meta is None:
        meta = sa.MetaData()

    sa.Table(
        'tasks', meta,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('done', sa.DateTime)
    )

    return meta
