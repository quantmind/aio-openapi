
from openapi.data.validate import validated_schema
from tests.example.models import SourcePrice


def test_prices() -> None:
    d = validated_schema(SourcePrice, dict(id=5432534, prices=dict(foo=45.68564)))
    assert d.prices
