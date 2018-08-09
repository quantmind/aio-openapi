import pytest

from openapi.db.columns import UUIDColumn


def test_runtime_error_with_incorrect_params():
    with pytest.raises(RuntimeError):
        UUIDColumn('test', primary_key=True, nullable=True)
