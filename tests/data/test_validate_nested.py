from decimal import Decimal

from openapi.data.validate import validated_schema
from tests.example.models import SourcePrice


def test_prices() -> None:
    d = validated_schema(SourcePrice, dict(id=5432534, prices=dict(foo=45.68564)))
    assert d.prices
    assert d.prices["foo"] == Decimal("45.6856")
    d = validated_schema(
        SourcePrice,
        dict(
            id=5432534,
            prices=dict(foo=45.68564),
            foos=[dict(text="test1", param=1), dict(text="test2", param="a")],
        ),
    )
    assert len(d.foos) == 2
    assert d.foos[0].text == "test1"
