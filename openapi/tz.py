from datetime import datetime

import pytz

UTC = pytz.utc


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC)
