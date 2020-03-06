from typing import Any, Dict, List, Tuple

import pytest

from openapi import utils
from openapi.db.container import Database
from openapi.exc import ImproperlyConfigured, JsonHttpException
from openapi.json import dumps
from openapi.utils import TypingInfo


def test_env():
    assert utils.get_env() == "test"


def test_debug_flag():
    assert utils.get_debug_flag() is False


def test_json_http_exception():
    ex = JsonHttpException(status=401)
    assert ex.status == 401
    assert ex.text == dumps({"message": "Unauthorized"})
    assert ex.headers["content-type"] == "application/json; charset=utf-8"


def test_json_http_exception_reason():
    ex = JsonHttpException(status=422, reason="non lo so")
    assert ex.status == 422
    assert ex.text == dumps({"message": "non lo so"})
    assert ex.headers["content-type"] == "application/json; charset=utf-8"


def test_exist_database_not_configured():
    db = Database()
    assert db.pool is None
    with pytest.raises(ImproperlyConfigured):
        db.engine


def test_replace_key():
    assert utils.replace_key({}, "foo", "bla") == {}
    assert utils.replace_key({"foo": 5}, "foo", "bla") == {"bla": 5}


def test_typing_info() -> None:
    assert TypingInfo.get(int) == utils.TypingInfo(int)
    assert TypingInfo.get(float) == utils.TypingInfo(float)
    assert TypingInfo.get(List[int]) == utils.TypingInfo(int, list)
    assert TypingInfo.get(Dict[str, int]) == utils.TypingInfo(int, dict)
    assert TypingInfo.get(List[Dict[str, int]]) == utils.TypingInfo(
        utils.TypingInfo(int, dict), list
    )
    assert TypingInfo.get(None) is None
    info = TypingInfo.get(List[int])
    assert TypingInfo.get(info) is info


def test_typing_info_dict_list() -> None:
    assert TypingInfo.get(Dict) == utils.TypingInfo(Any, dict)
    assert TypingInfo.get(List) == utils.TypingInfo(Any, list)


def test_bad_typing_info() -> None:
    with pytest.raises(TypeError):
        TypingInfo.get(1)
    with pytest.raises(TypeError):
        TypingInfo.get(Dict[int, int])
    with pytest.raises(TypeError):
        TypingInfo.get(Tuple[int, int])
