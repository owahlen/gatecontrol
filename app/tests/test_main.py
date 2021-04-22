import unittest
from unittest import mock
from unittest.mock import patch

from app.api import config


class TestAuth(unittest.TestCase):
    def test_init_default_host_port(self):
        # setup
        with patch('app.api.service.GateService'):
            from app import main
            with mock.patch.object(main, "uvicorn") as uvicorn_run_mock:
                with mock.patch.object(main, "__name__", "__main__"):
                    # when
                    main.init()
        # then
        uvicorn_run_mock.run.assert_called_once_with(main.app, host=config.DEFAULT_HOST, port=config.DEFAULT_PORT)
