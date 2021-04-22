import os
import unittest
from unittest.mock import patch

from app.api.config import HOST, DEFAULT_HOST, PORT, DEFAULT_PORT, config


class TestAuth(unittest.TestCase):

    def test_init_with_host_port(self):
        # setup
        os.environ[HOST] = '10.0.0.1'
        os.environ[PORT] = '1234'
        config.reload()
        with patch('app.api.service.GateService'):
            from app import main
            with patch.object(main, "uvicorn") as uvicorn_run_mock:
                with patch.object(main, "__name__", "__main__"):
                    # when
                    main.init()
        # then
        uvicorn_run_mock.run.assert_called_once_with(main.app, host='10.0.0.1', port='1234')
        # cleanup
        del os.environ[HOST]
        del os.environ[PORT]
        config.reload()

    def test_init_default_host_port(self):
        # setup
        with patch('app.api.service.GateService'):
            from app import main
            with patch.object(main, "uvicorn") as uvicorn_run_mock:
                with patch.object(main, "__name__", "__main__"):
                    # when
                    main.init()
        # then
        uvicorn_run_mock.run.assert_called_once_with(main.app, host=DEFAULT_HOST, port=DEFAULT_PORT)
