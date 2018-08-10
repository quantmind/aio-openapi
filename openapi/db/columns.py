import uuid

import sqlalchemy as sa
from sqlalchemy_utils import UUIDType


def UUIDColumn(
        name, primary_key=True, nullable=False, make_default=False, **kw):
    if primary_key and nullable:
        raise RuntimeError('Primary key must be NOT NULL')
    if make_default:
        kw.setdefault('default', uuid.uuid4)
    return sa.Column(
        name,
        UUIDType(),
        primary_key=primary_key,
        nullable=nullable,
        **kw
    )
