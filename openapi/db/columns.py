import uuid

import sqlalchemy as sa
from sqlalchemy_utils import UUIDType


def UUIDColumn(name, primary_key=True, nullable=False, make_default=False):
    if primary_key and nullable:
        raise RuntimeError('Primary key must be NOT NULL')
    return sa.Column(
        name,
        UUIDType(),
        primary_key=primary_key,
        nullable=nullable,
        default=uuid.uuid4 if make_default else None
    )
