from openapi.spec.utils import dedent, load_yaml_from_docstring, trim_docstring
from openapi.utils import compact, compact_dict


def test_compact():
    data = {"key1": "A", "key2": 1, "key3": None, "key4": False, "key5": True}
    expected = {"key1": "A", "key2": 1, "key5": True}
    new_data = compact(**data)
    assert new_data == expected


def test_compact_dict():
    data = {"key1": "A", "key2": 1, "key3": None, "key4": False, "key5": True}
    expected = {"key1": "A", "key2": 1, "key4": False, "key5": True}
    new_data = compact_dict(data)
    assert new_data == expected


def test_trim_docstring():
    docstring = "   test docstring\nline one\nline 2\nline 3    "
    expected = "test docstring\nline one\nline 2\nline 3"
    trimmed = trim_docstring(docstring)
    assert trimmed == expected


def test_dedent():
    docstring = " line one\n  line two\n    line three\n  line four"
    expected = "line one\nline two\n  line three\nline four"
    dedented = dedent(docstring)
    assert dedented == expected


def test_load_yaml_from_docstring():
    docstring = """
    This won't be on yaml: neither this
    ---
    keyA: something
    keyB:
        keyB1: nested1
        keyB2: nested2
    keyC: [item1, item2]
    """
    expected = {
        "keyA": "something",
        "keyB": {"keyB1": "nested1", "keyB2": "nested2"},
        "keyC": ["item1", "item2"],
    }
    yaml_data = load_yaml_from_docstring(docstring)
    assert yaml_data == expected


def test_load_yaml_from_docstring_invalid():
    docstring = """
    this is not a valid yaml docstring: docstring
    something here: else
    """
    yaml_data = load_yaml_from_docstring(docstring)
    assert yaml_data is None
