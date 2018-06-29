from openapi import utils
from openapi.exc import JsonHttpException
from openapi.json import dumps


def test_env():
    assert utils.get_env() == 'test'


def test_debug_flag():
    assert utils.get_debug_flag() is False


def test_json_http_exception():
    ex = JsonHttpException(status=401)
    assert ex.status == 401
    assert ex.text == dumps({'error': 'Unauthorized'})
    assert ex.headers['content-type'] == 'application/json; charset=utf-8'
