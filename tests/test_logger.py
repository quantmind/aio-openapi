from unittest.mock import patch

from click.testing import CliRunner

from openapi.logger import getLogger
from openapi.rest import rest


def test_logger():
    logger = getLogger()
    assert logger.name == "openapi"
    logger = getLogger("foo")
    assert logger.name == "openapi.foo"


def test_serve():
    runner = CliRunner()
    cli = rest(base_path="/v1")
    with patch("aiohttp.web.run_app") as mock:
        with patch("openapi.logger.logger.hasHandlers") as hasHandlers:
            hasHandlers.return_value = False
            with patch("openapi.logger.logger.addHandler") as addHandler:
                result = runner.invoke(cli, ["serve"])
                assert result.exit_code == 0
                assert mock.call_count == 1
                assert addHandler.call_count == 1
