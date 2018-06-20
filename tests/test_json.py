from datetime import datetime
from uuid import uuid4

import pytest

from openapi.json import encoder


def test_encoder_uuid():
    uuid = uuid4()
    encoded = encoder(uuid)
    assert encoded == uuid.hex


def test_encoder_datetime():
    now = datetime.now()
    encoded = encoder(now)
    assert encoded == now.isoformat()


def test_encoder_invalid_type():
    with pytest.raises(TypeError):
        encoder('string')
    with pytest.raises(TypeError):
        encoder(123)
    with pytest.raises(TypeError):
        encoder([1, 2, 3])
