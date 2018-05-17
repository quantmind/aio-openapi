from openapi import utils


def test_env():
    assert utils.get_env() == 'test'


def test_debug_flag():
    assert utils.get_debug_flag() is False
