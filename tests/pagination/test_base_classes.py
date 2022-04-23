from openapi.pagination import Pagination, Search, create_dataclass


def test_pagination():
    d = create_dataclass(None, {}, Pagination)
    assert isinstance(d, Pagination)
    assert d.apply(None) is None
    assert d.links(None, [], None) == {}


def test_search():
    d = create_dataclass(None, {}, Search)
    assert isinstance(d, Search)
    assert d.apply(None) is None
