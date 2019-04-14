from datetime import datetime

import pytz

UTC = pytz.utc


def utcnow():
    return datetime.now(tz=UTC)
