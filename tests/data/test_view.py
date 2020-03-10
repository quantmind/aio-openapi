import pytest

from openapi.data.view import DataView, ValidationErrors
from tests.example.models import Foo


def test_error() -> None:
    dv = DataView()
    with pytest.raises(RuntimeError):
        dv.cleaned(Foo, {}, Error=RuntimeError)

    with pytest.raises(TypeError):
        dv.raise_bad_data()

    with pytest.raises(RuntimeError):
        dv.raise_bad_data(exc=RuntimeError)

    with pytest.raises(ValidationErrors):
        dv.raiseValidationError()
